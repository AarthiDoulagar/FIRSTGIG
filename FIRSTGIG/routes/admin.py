from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import User, StudentProfile, Gig, Project, Payment, Review, Dispute
from decorators import role_required
from services.notify import notify
from services.escrow_service import release_payment, refund_payment
from services.reliability_service import recalculate_student, recalculate_client

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@role_required("admin")
def dashboard():
    students = User.query.filter_by(role="student").all()
    clients = User.query.filter_by(role="client").all()
    verified = StudentProfile.query.filter_by(verified=True).count()
    gigs = Gig.query.count()
    projects = Project.query.all()
    active = [p for p in projects if p.status in ("IN_PROGRESS", "ASSIGNED", "SUBMITTED")]
    completed = [p for p in projects if p.status == "COMPLETED"]
    overdue = [p for p in projects if p.status == "OVERDUE"]
    disputed = [p for p in projects if p.status == "DISPUTED"]
    payments = Payment.query.all()
    held = sum(p.amount for p in payments if p.status in ("Held", "Refund Requested", "Pending"))
    released = sum(p.amount for p in payments if p.status == "Released")
    refunded = sum(p.amount for p in payments if p.status == "Refunded")
    open_disputes = Dispute.query.filter(Dispute.status != "Resolved").count()

    by_status = {}
    for p in projects:
        by_status[p.status] = by_status.get(p.status, 0) + 1

    return render_template(
        "admin/dashboard.html",
        student_count=len(students),
        client_count=len(clients),
        verified=verified,
        gigs=gigs,
        active=len(active),
        completed=len(completed),
        overdue=len(overdue),
        disputed=len(disputed),
        held=held,
        released=released,
        refunded=refunded,
        open_disputes=open_disputes,
        by_status=by_status,
        recent_projects=Project.query.order_by(Project.created_at.desc()).limit(8).all(),
    )


@admin_bp.route("/users")
@login_required
@role_required("admin")
def users():
    role = request.args.get("role")
    q = User.query
    if role in ("student", "client", "admin"):
        q = q.filter_by(role=role)
    users = q.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users, role=role)


@admin_bp.route("/users/<int:user_id>/verify", methods=["POST"])
@login_required
@role_required("admin")
def verify_student(user_id):
    user = User.query.get_or_404(user_id)
    if user.student_profile:
        user.student_profile.verified = True
        user.student_profile.verification_code = None
        notify(user.id, "An admin verified your student status.", "/profile")
        db.session.commit()
        flash(f"{user.name} is now a Verified Student.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/suspend", methods=["POST"])
@login_required
@role_required("admin")
def suspend(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot suspend yourself.", "warning")
        return redirect(url_for("admin.users"))
    user.is_active_account = not user.is_active_account
    db.session.commit()
    flash(("Account reactivated." if user.is_active_account else "Account suspended."), "info")
    return redirect(url_for("admin.users"))


@admin_bp.route("/gigs")
@login_required
@role_required("admin")
def gigs_list():
    gigs = Gig.query.order_by(Gig.created_at.desc()).all()
    return render_template("admin/gigs.html", gigs=gigs)


@admin_bp.route("/gigs/<int:gig_id>/remove", methods=["POST"])
@login_required
@role_required("admin")
def remove_gig(gig_id):
    gig = Gig.query.get_or_404(gig_id)
    gig.status = "REMOVED"
    db.session.commit()
    flash("Gig removed from the marketplace.", "info")
    return redirect(url_for("admin.gigs_list"))


@admin_bp.route("/projects")
@login_required
@role_required("admin")
def projects_list():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template("admin/projects.html", projects=projects)


@admin_bp.route("/disputes")
@login_required
@role_required("admin")
def disputes_list():
    disputes = Dispute.query.order_by(Dispute.created_at.desc()).all()
    return render_template("admin/disputes.html", disputes=disputes)


@admin_bp.route("/disputes/<int:dispute_id>/review", methods=["POST"])
@login_required
@role_required("admin")
def mark_review(dispute_id):
    d = Dispute.query.get_or_404(dispute_id)
    d.status = "Under Review"
    db.session.commit()
    flash("Dispute marked under review.", "info")
    return redirect(url_for("admin.disputes_list"))


@admin_bp.route("/disputes/<int:dispute_id>/resolve", methods=["POST"])
@login_required
@role_required("admin")
def resolve(dispute_id):
    d = Dispute.query.get_or_404(dispute_id)
    project = d.project
    decision = request.form.get("decision")
    d.status = "Resolved"
    d.resolved_at = datetime.utcnow()
    d.admin_decision = decision

    if decision == "Refund Client":
        refund_payment(project)
        recalculate_student(project.student_id)
    elif decision == "Release Payment":
        project.status = "COMPLETED"
        project.completed_at = datetime.utcnow()
        release_payment(project)
        if project.gig:
            project.gig.status = "CLOSED"
        recalculate_student(project.student_id)
    elif decision == "Extend Deadline":
        project.deadline = project.deadline + timedelta(days=7)
        project.status = "IN_PROGRESS"
        if project.payment and project.payment.status == "Refund Requested":
            project.payment.status = "Held"
    elif decision == "Mark Project Completed":
        project.status = "COMPLETED"
        project.completed_at = datetime.utcnow()
        release_payment(project)
        if project.gig:
            project.gig.status = "CLOSED"
        recalculate_student(project.student_id)
    else:
        flash("Choose a valid decision.", "danger")
        return redirect(url_for("admin.disputes_list"))

    notify(project.client_id, f"Dispute resolved: {decision}.", f"/projects/{project.id}")
    notify(project.student_id, f"Dispute resolved: {decision}.", f"/projects/{project.id}")
    db.session.commit()
    flash(f"Dispute resolved — {decision}.", "success")
    return redirect(url_for("admin.disputes_list"))


@admin_bp.route("/reviews")
@login_required
@role_required("admin")
def reviews_list():
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template("admin/reviews.html", reviews=reviews)


@admin_bp.route("/reviews/<int:review_id>/remove", methods=["POST"])
@login_required
@role_required("admin")
def remove_review(review_id):
    review = Review.query.get_or_404(review_id)
    uid = review.reviewed_user_id
    db.session.delete(review)
    db.session.commit()
    user = User.query.get(uid)
    if user and user.is_student():
        recalculate_student(uid)
    elif user and user.is_client():
        recalculate_client(uid)
    flash("Review removed.", "info")
    return redirect(url_for("admin.reviews_list"))
