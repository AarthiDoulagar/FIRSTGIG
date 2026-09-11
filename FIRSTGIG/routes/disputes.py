from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import Project, Dispute
from services.notify import notify

disputes_bp = Blueprint("disputes", __name__)

REASONS = [
    "Student missed deadline",
    "Client refuses to approve valid work",
    "Work does not match requirements",
    "Payment needs intervention",
]


@disputes_bp.route("/projects/<int:project_id>/dispute", methods=["GET", "POST"])
@login_required
def create_dispute(project_id):
    project = Project.query.get_or_404(project_id)
    if not project.is_participant(current_user.id):
        flash("Only project participants can raise a dispute.", "danger")
        return redirect(url_for("projects.list_projects"))
    if project.status in ("COMPLETED", "REFUNDED", "CANCELLED"):
        flash("This project is already closed.", "warning")
        return redirect(url_for("projects.detail", project_id=project.id))
    existing = Dispute.query.filter_by(project_id=project.id).filter(Dispute.status != "Resolved").first()
    if existing:
        flash("An open dispute already exists for this project.", "info")
        return redirect(url_for("disputes.detail", dispute_id=existing.id))

    if request.method == "POST":
        reason = request.form.get("reason") or REASONS[0]
        description = (request.form.get("description") or "").strip()
        evidence = (request.form.get("evidence") or "").strip()
        if len(description) < 10:
            flash("Describe the issue in more detail.", "danger")
            return render_template("disputes/create.html", project=project, reasons=REASONS)
        d = Dispute(
            project_id=project.id,
            raised_by=current_user.id,
            reason=reason,
            description=description,
            evidence=evidence,
            status="Open",
        )
        db.session.add(d)
        project.status = "DISPUTED"
        other = project.student_id if current_user.id == project.client_id else project.client_id
        notify(other, f"A dispute was opened on “{project.gig.title}”.", f"/projects/{project.id}")
        db.session.commit()
        flash("Dispute opened. An admin will review it.", "warning")
        return redirect(url_for("disputes.detail", dispute_id=d.id))
    return render_template("disputes/create.html", project=project, reasons=REASONS)


@disputes_bp.route("/disputes/<int:dispute_id>")
@login_required
def detail(dispute_id):
    d = Dispute.query.get_or_404(dispute_id)
    project = d.project
    if not current_user.is_admin() and not project.is_participant(current_user.id):
        flash("Unauthorized.", "danger")
        return redirect(url_for("main.dashboard_redirect"))
    return render_template("disputes/detail.html", dispute=d, project=project)
