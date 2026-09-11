from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import Project, Application, Gig, Review, Portfolio
from decorators import role_required
from services.level_service import level_for_completed, LEVELS
from services.recommendation_service import recommend_gigs

student_bp = Blueprint("student", __name__)


@student_bp.route("/dashboard")
@login_required
@role_required("student")
def dashboard():
    profile = current_user.student_profile
    level = level_for_completed(profile.completed_gigs)
    recs = recommend_gigs(current_user, limit=4)
    my_apps = Application.query.filter_by(student_id=current_user.id).order_by(Application.created_at.desc()).limit(8).all()
    my_projects = Project.query.filter_by(student_id=current_user.id).order_by(Project.created_at.desc()).all()
    active = [p for p in my_projects if p.status in ("IN_PROGRESS", "ASSIGNED", "SUBMITTED", "OVERDUE", "DISPUTED")]
    return render_template(
        "student/dashboard.html",
        profile=profile,
        level=level,
        levels=LEVELS,
        recs=recs,
        applications=my_apps,
        projects=active,
        all_projects=my_projects,
    )


@student_bp.route("/profile", methods=["GET", "POST"])
@login_required
@role_required("student")
def profile():
    profile = current_user.student_profile
    if request.method == "POST":
        current_user.name = (request.form.get("name") or current_user.name).strip()
        profile.bio = (request.form.get("bio") or "").strip()
        profile.skills = (request.form.get("skills") or "").strip()
        profile.interests = (request.form.get("interests") or "").strip()
        profile.college = (request.form.get("college") or profile.college).strip()
        profile.branch = (request.form.get("branch") or profile.branch).strip()
        profile.academic_year = (request.form.get("academic_year") or profile.academic_year).strip()
        db.session.commit()
        flash("Profile updated. Your freelancer level cannot be edited — it is earned.", "success")
        return redirect(url_for("student.profile"))
    level = level_for_completed(profile.completed_gigs)
    reviews = Review.query.filter_by(reviewed_user_id=current_user.id).order_by(Review.created_at.desc()).all()
    completed = Project.query.filter_by(student_id=current_user.id, status="COMPLETED").all()
    portfolio = profile.portfolio_items.order_by(Portfolio.id.desc()).all()
    return render_template(
        "student/profile.html",
        profile=profile,
        level=level,
        levels=LEVELS,
        reviews=reviews,
        completed=completed,
        portfolio=portfolio,
        editable=True,
    )


@student_bp.route("/u/<int:user_id>")
def public_profile(user_id):
    from models import User

    user = User.query.get_or_404(user_id)
    if not user.is_student() or not user.student_profile:
        flash("Student profile not found.", "warning")
        return redirect(url_for("gigs.marketplace"))
    profile = user.student_profile
    level = level_for_completed(profile.completed_gigs)
    reviews = Review.query.filter_by(reviewed_user_id=user.id).order_by(Review.created_at.desc()).all()
    completed = Project.query.filter_by(student_id=user.id, status="COMPLETED").all()
    portfolio = [p for p in profile.portfolio_items.all() if p.is_public]
    return render_template(
        "student/profile.html",
        profile=profile,
        level=level,
        levels=LEVELS,
        reviews=reviews,
        completed=completed,
        portfolio=portfolio,
        editable=False,
        viewed_user=user,
    )
