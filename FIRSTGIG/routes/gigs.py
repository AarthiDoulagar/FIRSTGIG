from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import Gig, Application, Project, Milestone
from decorators import role_required
from services.notify import notify
from services.escrow_service import create_held_payment
from services.level_service import level_for_completed
from services.recommendation_service import recommend_gigs

gigs_bp = Blueprint("gigs", __name__)

CATEGORIES = [
    "Web Development",
    "UI/UX Design",
    "Content Writing",
    "Data Analysis",
    "Mobile Apps",
    "Backend Development",
    "Marketing",
    "Research",
]


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


@gigs_bp.route("/gigs")
def marketplace():
    q = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip()
    skill = (request.args.get("skill") or "").strip()
    difficulty = (request.args.get("difficulty") or "").strip()
    budget = (request.args.get("budget") or "").strip()
    deadline_filter = (request.args.get("deadline") or "").strip()

    query = Gig.query.filter(Gig.status.in_(["OPEN", "APPLIED"]))
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Gig.title.ilike(like), Gig.description.ilike(like), Gig.required_skills.ilike(like)))
    if category:
        query = query.filter(Gig.category == category)
    if skill:
        query = query.filter(Gig.required_skills.ilike(f"%{skill}%"))
    if difficulty:
        query = query.filter(Gig.difficulty == difficulty)
    if budget == "under5":
        query = query.filter(Gig.budget <= 5000)
    elif budget == "5to15":
        query = query.filter(Gig.budget > 5000, Gig.budget <= 15000)
    elif budget == "15plus":
        query = query.filter(Gig.budget > 15000)
    if deadline_filter == "week":
        query = query.filter(Gig.deadline <= date.today().replace(day=min(date.today().day + 7, 28)))
    gigs = query.order_by(Gig.created_at.desc()).all()

    recs = []
    if current_user.is_authenticated and current_user.is_student():
        recs = recommend_gigs(current_user, limit=3)
        student_level = level_for_completed(current_user.student_profile.completed_gigs)
    else:
        student_level = None

    return render_template(
        "gigs/marketplace.html",
        gigs=gigs,
        recs=recs,
        categories=CATEGORIES,
        student_level=student_level,
        filters={"q": q, "category": category, "skill": skill, "difficulty": difficulty, "budget": budget, "deadline": deadline_filter},
    )


@gigs_bp.route("/gigs/new", methods=["GET", "POST"])
@login_required
@role_required("client")
def post_gig():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        category = (request.form.get("category") or "").strip()
        skills = (request.form.get("required_skills") or "").strip()
        requirements = (request.form.get("requirements") or "").strip()
        difficulty = request.form.get("difficulty") or "Beginner"
        try:
            budget = int(request.form.get("budget") or 0)
        except ValueError:
            budget = 0
        deadline = _parse_date(request.form.get("deadline"))
        try:
            milestone_count = max(1, int(request.form.get("milestone_count") or 1))
        except ValueError:
            milestone_count = 1

        if not title or not description or not category:
            flash("Title, description, and category are required.", "danger")
            return render_template("gigs/post.html", categories=CATEGORIES)
        if budget < 500:
            flash("Budget must be at least ₹500.", "danger")
            return render_template("gigs/post.html", categories=CATEGORIES)
        if not deadline or deadline < date.today():
            flash("Choose a deadline in the future.", "danger")
            return render_template("gigs/post.html", categories=CATEGORIES)

        gig = Gig(
            client_id=current_user.id,
            title=title,
            description=description,
            category=category,
            required_skills=skills,
            budget=budget,
            deadline=deadline,
            difficulty=difficulty,
            status="OPEN",
            requirements=requirements,
            milestone_count=milestone_count,
        )
        db.session.add(gig)
        db.session.commit()
        flash("Gig posted. Students can apply from the marketplace.", "success")
        return redirect(url_for("gigs.detail", gig_id=gig.id))
    return render_template("gigs/post.html", categories=CATEGORIES)


@gigs_bp.route("/gigs/manage")
@login_required
@role_required("client")
def manage():
    gigs = Gig.query.filter_by(client_id=current_user.id).order_by(Gig.created_at.desc()).all()
    return render_template("gigs/manage.html", gigs=gigs)


@gigs_bp.route("/gigs/<int:gig_id>")
def detail(gig_id):
    gig = Gig.query.get_or_404(gig_id)
    already = None
    if current_user.is_authenticated and current_user.is_student():
        already = Application.query.filter_by(gig_id=gig.id, student_id=current_user.id).first()
    return render_template("gigs/detail.html", gig=gig, already=already)


@gigs_bp.route("/gigs/<int:gig_id>/apply", methods=["POST"])
@login_required
@role_required("student")
def apply(gig_id):
    gig = Gig.query.get_or_404(gig_id)
    if gig.status not in ("OPEN", "APPLIED"):
        flash("This gig is no longer accepting applications.", "warning")
        return redirect(url_for("gigs.detail", gig_id=gig.id))
    existing = Application.query.filter_by(gig_id=gig.id, student_id=current_user.id).first()
    if existing:
        flash("You already applied to this gig.", "info")
        return redirect(url_for("gigs.detail", gig_id=gig.id))
    proposal = (request.form.get("proposal") or "").strip()
    expected = (request.form.get("expected_completion") or "").strip()
    if len(proposal) < 20:
        flash("Write a short proposal (at least 20 characters).", "danger")
        return redirect(url_for("gigs.detail", gig_id=gig.id))
    if not expected:
        flash("Expected completion time is required.", "danger")
        return redirect(url_for("gigs.detail", gig_id=gig.id))
    app = Application(
        gig_id=gig.id,
        student_id=current_user.id,
        proposal=proposal,
        expected_completion=expected,
        status="Pending",
    )
    db.session.add(app)
    if gig.status == "OPEN":
        gig.status = "APPLIED"
    notify(gig.client_id, f"{current_user.name} applied to “{gig.title}”.", f"/gigs/{gig.id}/applicants")
    db.session.commit()
    flash("Application sent.", "success")
    return redirect(url_for("gigs.detail", gig_id=gig.id))


@gigs_bp.route("/gigs/<int:gig_id>/applicants")
@login_required
@role_required("client")
def applicants(gig_id):
    gig = Gig.query.get_or_404(gig_id)
    if gig.client_id != current_user.id:
        flash("You can only view applicants for your own gigs.", "danger")
        return redirect(url_for("gigs.manage"))
    apps = Application.query.filter_by(gig_id=gig.id).order_by(Application.created_at.desc()).all()
    cards = []
    for a in apps:
        sp = a.student.student_profile
        cards.append({"app": a, "level": level_for_completed(sp.completed_gigs if sp else 0), "profile": sp})
    return render_template("gigs/applicants.html", gig=gig, cards=cards)


@gigs_bp.route("/gigs/<int:gig_id>/applications/<int:app_id>/accept", methods=["POST"])
@login_required
@role_required("client")
def accept(gig_id, app_id):
    gig = Gig.query.get_or_404(gig_id)
    if gig.client_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("gigs.manage"))
    if gig.status == "ASSIGNED":
        flash("This gig already has a hired student.", "warning")
        return redirect(url_for("gigs.applicants", gig_id=gig.id))
    application = Application.query.get_or_404(app_id)
    if application.gig_id != gig.id or application.status != "Pending":
        flash("This application cannot be accepted.", "warning")
        return redirect(url_for("gigs.applicants", gig_id=gig.id))

    application.status = "Accepted"
    for other in Application.query.filter_by(gig_id=gig.id).all():
        if other.id != application.id and other.status == "Pending":
            other.status = "Rejected"
            notify(other.student_id, f"Your application for “{gig.title}” was not selected.", f"/gigs/{gig.id}")

    gig.status = "ASSIGNED"
    project = Project(
        gig_id=gig.id,
        client_id=current_user.id,
        student_id=application.student_id,
        budget=gig.budget,
        start_date=date.today(),
        deadline=gig.deadline,
        status="IN_PROGRESS",
    )
    db.session.add(project)
    db.session.flush()
    create_held_payment(project)

    n = max(1, gig.milestone_count or 1)
    split = gig.budget // n
    remainder = gig.budget - split * n
    for i in range(n):
        amt = split + (remainder if i == n - 1 else 0)
        db.session.add(
            Milestone(
                project_id=project.id,
                title=f"Milestone {i + 1}",
                description=f"Phase {i + 1} of {gig.title}",
                amount=amt,
                deadline=gig.deadline,
                status="In Progress" if i == 0 else "Pending",
            )
        )

    notify(application.student_id, f"You were hired for “{gig.title}”. Mock escrow is holding ₹{gig.budget:,}.", f"/projects/{project.id}")
    db.session.commit()
    flash("Student hired. Project created and mock escrow is holding the budget.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))


@gigs_bp.route("/gigs/<int:gig_id>/applications/<int:app_id>/reject", methods=["POST"])
@login_required
@role_required("client")
def reject(gig_id, app_id):
    gig = Gig.query.get_or_404(gig_id)
    if gig.client_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("gigs.manage"))
    application = Application.query.get_or_404(app_id)
    if application.gig_id != gig.id:
        flash("Invalid application.", "danger")
        return redirect(url_for("gigs.applicants", gig_id=gig.id))
    application.status = "Rejected"
    notify(application.student_id, f"Your application for “{gig.title}” was declined.", f"/gigs/{gig.id}")
    db.session.commit()
    flash("Application rejected.", "info")
    return redirect(url_for("gigs.applicants", gig_id=gig.id))
