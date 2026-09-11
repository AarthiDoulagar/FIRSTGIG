from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from extensions import db
from models import Project, Milestone, Review, Portfolio, Dispute
from decorators import role_required
from services.notify import notify
from services.escrow_service import release_payment, request_refund
from services.reliability_service import recalculate_student, recalculate_client
from services.level_service import level_for_completed

projects_bp = Blueprint("projects", __name__)


def _allowed(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


@projects_bp.route("/projects")
@login_required
def list_projects():
    if current_user.is_admin():
        projects = Project.query.order_by(Project.created_at.desc()).all()
    elif current_user.is_client():
        projects = Project.query.filter_by(client_id=current_user.id).order_by(Project.created_at.desc()).all()
    else:
        projects = Project.query.filter_by(student_id=current_user.id).order_by(Project.created_at.desc()).all()
    return render_template("projects/list.html", projects=projects)


@projects_bp.route("/projects/<int:project_id>")
@login_required
def detail(project_id):
    project = Project.query.get_or_404(project_id)
    if not current_user.is_admin() and not project.is_participant(current_user.id):
        flash("You do not have access to this project.", "danger")
        return redirect(url_for("projects.list_projects"))
    my_review = Review.query.filter_by(project_id=project.id, reviewer_id=current_user.id).first()
    can_review = project.status == "COMPLETED" and project.is_participant(current_user.id) and not my_review
    portfolio_item = None
    if current_user.is_student() and current_user.student_profile:
        portfolio_item = Portfolio.query.filter_by(project_id=project.id, student_id=current_user.student_profile.id).first()
    student_level = level_for_completed(project.student.student_profile.completed_gigs if project.student.student_profile else 0)
    open_dispute = Dispute.query.filter_by(project_id=project.id).filter(Dispute.status != "Resolved").first()
    return render_template(
        "projects/detail.html",
        project=project,
        can_review=can_review,
        my_review=my_review,
        portfolio_item=portfolio_item,
        student_level=student_level,
        open_dispute=open_dispute,
    )


@projects_bp.route("/projects/<int:project_id>/submit", methods=["POST"])
@login_required
@role_required("student")
def submit_work(project_id):
    project = Project.query.get_or_404(project_id)
    if project.student_id != current_user.id:
        flash("Only the hired student can submit work.", "danger")
        return redirect(url_for("projects.list_projects"))
    if project.status not in ("IN_PROGRESS", "ASSIGNED", "OVERDUE"):
        flash("This project cannot be submitted in its current status.", "warning")
        return redirect(url_for("projects.detail", project_id=project.id))
    message = (request.form.get("submission_message") or "").strip()
    link = (request.form.get("submission_link") or "").strip()
    if len(message) < 10:
        flash("Add a short submission description.", "danger")
        return redirect(url_for("projects.detail", project_id=project.id))
    file = request.files.get("submission_file")
    filename = None
    if file and file.filename:
        if not _allowed(file.filename):
            flash("File type not allowed.", "danger")
            return redirect(url_for("projects.detail", project_id=project.id))
        filename = secure_filename(f"p{project.id}_" + file.filename)
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], "submissions", filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        file.save(path)
    project.submission_message = message
    project.submission_link = link
    project.submission_file = filename
    project.submitted_at = datetime.utcnow()
    project.status = "SUBMITTED"
    for m in project.milestones:
        if m.status != "Approved":
            m.status = "Submitted"
    notify(project.client_id, f"{current_user.name} submitted work on “{project.gig.title}”.", f"/projects/{project.id}")
    db.session.commit()
    flash("Work submitted. Waiting for client approval.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))


@projects_bp.route("/projects/<int:project_id>/approve", methods=["POST"])
@login_required
@role_required("client")
def approve(project_id):
    project = Project.query.get_or_404(project_id)
    if project.client_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("projects.list_projects"))
    if project.status not in ("SUBMITTED", "IN_PROGRESS", "OVERDUE"):
        flash("This project cannot be approved yet.", "warning")
        return redirect(url_for("projects.detail", project_id=project.id))
    project.status = "COMPLETED"
    project.completed_at = datetime.utcnow()
    for m in project.milestones:
        m.status = "Approved"
    release_payment(project)
    if project.gig:
        project.gig.status = "CLOSED"
    recalculate_student(project.student_id)
    notify(project.student_id, f"“{project.gig.title}” was approved. Mock escrow released. You can leave a review.", f"/projects/{project.id}")
    notify(project.client_id, "Project completed. Please leave a verified review.", f"/projects/{project.id}/review")
    db.session.commit()
    flash("Project completed. Mock escrow released. Reviews are now unlocked.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))


@projects_bp.route("/projects/<int:project_id>/changes", methods=["POST"])
@login_required
@role_required("client")
def request_changes(project_id):
    project = Project.query.get_or_404(project_id)
    if project.client_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("projects.list_projects"))
    if project.status != "SUBMITTED":
        flash("Request changes only after a submission.", "warning")
        return redirect(url_for("projects.detail", project_id=project.id))
    note = (request.form.get("change_request") or "").strip()
    if not note:
        flash("Describe the changes you need.", "danger")
        return redirect(url_for("projects.detail", project_id=project.id))
    project.change_request = note
    project.status = "IN_PROGRESS"
    notify(project.student_id, f"Changes requested on “{project.gig.title}”.", f"/projects/{project.id}")
    db.session.commit()
    flash("Change request sent. Project is back in progress.", "info")
    return redirect(url_for("projects.detail", project_id=project.id))


@projects_bp.route("/projects/<int:project_id>/explain", methods=["POST"])
@login_required
@role_required("student")
def explain(project_id):
    project = Project.query.get_or_404(project_id)
    if project.student_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("projects.list_projects"))
    text = (request.form.get("student_explanation") or "").strip()
    if not text:
        flash("Write a short explanation or extension request.", "danger")
        return redirect(url_for("projects.detail", project_id=project.id))
    project.student_explanation = text
    notify(project.client_id, f"{current_user.name} sent an explanation on project #{project.id}.", f"/projects/{project.id}")
    db.session.commit()
    flash("Explanation saved. The client and admin can see it.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))


@projects_bp.route("/projects/<int:project_id>/extend-request", methods=["POST"])
@login_required
@role_required("student")
def request_extension(project_id):
    project = Project.query.get_or_404(project_id)
    if project.student_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("projects.list_projects"))
    days = int(request.form.get("days") or 3)
    project.student_explanation = (project.student_explanation or "") + f"\n[Extension requested: +{days} days]"
    notify(project.client_id, f"Extension of {days} days requested on project #{project.id}.", f"/projects/{project.id}")
    db.session.commit()
    flash("Extension requested. The client can grant it, or raise a dispute for admin review.", "info")
    return redirect(url_for("projects.detail", project_id=project.id))


@projects_bp.route("/projects/<int:project_id>/grant-extension", methods=["POST"])
@login_required
@role_required("client")
def grant_extension(project_id):
    project = Project.query.get_or_404(project_id)
    if project.client_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("projects.list_projects"))
    days = int(request.form.get("days") or 3)
    project.deadline = project.deadline + timedelta(days=days)
    if project.status == "OVERDUE":
        project.status = "IN_PROGRESS"
    notify(project.student_id, f"Deadline extended by {days} days.", f"/projects/{project.id}")
    db.session.commit()
    flash(f"Deadline extended by {days} days.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))


@projects_bp.route("/projects/<int:project_id>/refund", methods=["POST"])
@login_required
@role_required("client")
def refund_request(project_id):
    project = Project.query.get_or_404(project_id)
    if project.client_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("projects.list_projects"))
    if project.status not in ("OVERDUE", "DISPUTED", "IN_PROGRESS", "SUBMITTED"):
        flash("Refund can be requested for active or overdue work.", "warning")
        return redirect(url_for("projects.detail", project_id=project.id))
    request_refund(project)
    reason = (request.form.get("reason") or "Refund requested after deadline / quality concern.").strip()
    existing = Dispute.query.filter_by(project_id=project.id).filter(Dispute.status != "Resolved").first()
    if not existing:
        d = Dispute(
            project_id=project.id,
            raised_by=current_user.id,
            reason="Payment needs intervention",
            description=reason,
            evidence="Client requested mock escrow refund.",
            status="Open",
        )
        db.session.add(d)
        project.status = "DISPUTED"
        notify(project.student_id, "Client requested a refund. A dispute was opened.", f"/projects/{project.id}")
    db.session.commit()
    flash("Refund requested. Mock escrow is marked Refund Requested and a dispute was opened for admin.", "warning")
    return redirect(url_for("projects.detail", project_id=project.id))


@projects_bp.route("/projects/<int:project_id>/milestones/<int:mid>/status", methods=["POST"])
@login_required
def milestone_status(project_id, mid):
    project = Project.query.get_or_404(project_id)
    if not project.is_participant(current_user.id) and not current_user.is_admin():
        flash("Unauthorized.", "danger")
        return redirect(url_for("projects.list_projects"))
    m = Milestone.query.get_or_404(mid)
    if m.project_id != project.id:
        flash("Invalid milestone.", "danger")
        return redirect(url_for("projects.detail", project_id=project.id))
    new_status = request.form.get("status")
    allowed = {
        "student": ["In Progress", "Submitted"],
        "client": ["Approved", "In Progress"],
        "admin": ["Pending", "In Progress", "Submitted", "Approved"],
    }
    role = current_user.role
    if new_status not in allowed.get(role, []):
        flash("You cannot set that milestone status.", "danger")
        return redirect(url_for("projects.detail", project_id=project.id))
    m.status = new_status
    db.session.commit()
    flash("Milestone updated.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))


@projects_bp.route("/projects/<int:project_id>/portfolio", methods=["POST"])
@login_required
@role_required("student")
def add_portfolio(project_id):
    project = Project.query.get_or_404(project_id)
    if project.student_id != current_user.id or project.status != "COMPLETED":
        flash("Only completed projects can be added to your portfolio.", "warning")
        return redirect(url_for("projects.detail", project_id=project.id))
    profile = current_user.student_profile
    existing = Portfolio.query.filter_by(project_id=project.id, student_id=profile.id).first()
    if existing:
        existing.is_public = request.form.get("is_public") == "on"
        existing.contribution = (request.form.get("contribution") or existing.contribution).strip()
        existing.project_link = (request.form.get("project_link") or existing.project_link or "").strip()
        db.session.commit()
        flash("Portfolio item updated.", "success")
        return redirect(url_for("student.profile"))
    client_review = Review.query.filter_by(project_id=project.id, reviewed_user_id=current_user.id).first()
    item = Portfolio(
        student_id=profile.id,
        project_id=project.id,
        title=project.gig.title if project.gig else f"Project #{project.id}",
        description=project.gig.description if project.gig else "",
        skills=project.gig.required_skills if project.gig else "",
        is_public=request.form.get("is_public") == "on",
        project_link=request.form.get("project_link") or project.submission_link,
        contribution=(request.form.get("contribution") or "Delivered the full project scope.").strip(),
        completion_date=project.completed_at.date() if project.completed_at else date.today(),
        client_review=client_review.comment if client_review else None,
    )
    db.session.add(item)
    db.session.commit()
    flash("Added to your portfolio.", "success")
    return redirect(url_for("student.profile"))
