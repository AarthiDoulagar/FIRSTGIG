from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import Project, Review
from services.notify import notify
from services.reliability_service import recalculate_student, recalculate_client

reviews_bp = Blueprint("reviews", __name__)


def _can_review(project, user):
    if project.status != "COMPLETED":
        return False, "Reviews unlock only after a project is completed."
    if not project.is_participant(user.id):
        return False, "Only the client and hired student can review this project."
    existing = Review.query.filter_by(project_id=project.id, reviewer_id=user.id).first()
    if existing:
        return False, "You already submitted a review for this project."
    return True, ""


@reviews_bp.route("/projects/<int:project_id>/review", methods=["GET", "POST"])
@login_required
def create_review(project_id):
    project = Project.query.get_or_404(project_id)
    ok, msg = _can_review(project, current_user)
    if not ok:
        flash(msg, "warning")
        return redirect(url_for("projects.detail", project_id=project.id))

    other_id = project.student_id if current_user.id == project.client_id else project.client_id

    if request.method == "POST":
        try:
            rating = int(request.form.get("rating") or 0)
        except ValueError:
            rating = 0
        comment = (request.form.get("comment") or "").strip()
        if rating < 1 or rating > 5:
            flash("Rating must be between 1 and 5.", "danger")
            return render_template("reviews/form.html", project=project)
        if len(comment) < 8:
            flash("Please write a short comment.", "danger")
            return render_template("reviews/form.html", project=project)
        review = Review(
            project_id=project.id,
            reviewer_id=current_user.id,
            reviewed_user_id=other_id,
            rating=rating,
            comment=comment,
        )
        db.session.add(review)
        db.session.commit()
        if current_user.id == project.client_id:
            recalculate_student(project.student_id)
        else:
            recalculate_client(project.client_id)
        notify(other_id, f"{current_user.name} left a verified review.", f"/projects/{project.id}")
        db.session.commit()
        flash("Verified review submitted.", "success")
        return redirect(url_for("projects.detail", project_id=project.id))

    return render_template("reviews/form.html", project=project)
