from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import User, StudentProfile, ClientProfile
from services.notify import notify
import random

auth_bp = Blueprint("auth", __name__)


def _email_taken(email):
    return User.query.filter_by(email=email.lower().strip()).first() is not None


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard_redirect"))
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")
        if not user.is_active_account:
            flash("This account has been suspended. Contact admin.", "danger")
            return render_template("auth/login.html")
        login_user(user)
        flash(f"Welcome back, {user.name.split()[0]}.", "success")
        next_url = request.args.get("next")
        return redirect(next_url or url_for("main.dashboard_redirect"))
    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/register/student", methods=["GET", "POST"])
def register_student():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard_redirect"))
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        college = (request.form.get("college") or "").strip()
        branch = (request.form.get("branch") or "").strip()
        year = (request.form.get("academic_year") or "").strip()
        bio = (request.form.get("bio") or "").strip()
        skills = (request.form.get("skills") or "").strip()
        interests = (request.form.get("interests") or "").strip()
        college_email = (request.form.get("college_email") or email).strip().lower()

        errors = []
        if len(name) < 2:
            errors.append("Enter your full name.")
        if "@" not in email:
            errors.append("Enter a valid email.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if not college or not branch or not year:
            errors.append("College, branch, and year are required.")
        if _email_taken(email):
            errors.append("That email is already registered.")
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register_student.html")

        user = User(name=name, email=email, role="student")
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        code = f"{random.randint(100000, 999999)}"
        profile = StudentProfile(
            user_id=user.id,
            college=college,
            branch=branch,
            academic_year=year,
            bio=bio,
            skills=skills,
            interests=interests,
            college_email=college_email,
            verification_code=code,
            verified=False,
        )
        db.session.add(profile)
        notify(user.id, "Welcome to FirstGig. Verify your college email to earn the Verified Student badge.", "/verify-college")
        db.session.commit()
        login_user(user)
        flash(f"Account created. Demo verification code (mock): {code}", "success")
        return redirect(url_for("auth.verify_college"))
    return render_template("auth/register_student.html")


@auth_bp.route("/register/client", methods=["GET", "POST"])
def register_client():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard_redirect"))
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        company = (request.form.get("company_name") or "").strip()
        description = (request.form.get("description") or "").strip()
        errors = []
        if len(name) < 2:
            errors.append("Enter your name.")
        if "@" not in email:
            errors.append("Enter a valid email.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if not company:
            errors.append("Company / business name is required.")
        if _email_taken(email):
            errors.append("That email is already registered.")
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register_client.html")
        user = User(name=name, email=email, role="client")
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        db.session.add(ClientProfile(user_id=user.id, company_name=company, description=description))
        notify(user.id, "Welcome to FirstGig. Post a gig to hire verified students.", "/gigs/new")
        db.session.commit()
        login_user(user)
        flash("Client account created. You can post a gig now.", "success")
        return redirect(url_for("client.dashboard"))
    return render_template("auth/register_client.html")


@auth_bp.route("/verify-college", methods=["GET", "POST"])
@login_required
def verify_college():
    if not current_user.is_student():
        flash("Only students verify a college email.", "warning")
        return redirect(url_for("main.dashboard_redirect"))
    profile = current_user.student_profile
    if profile.verified:
        flash("Your college email is already verified.", "info")
        return redirect(url_for("student.profile"))
    if request.method == "POST":
        code = (request.form.get("code") or "").strip()
        if code and code == profile.verification_code:
            profile.verified = True
            profile.verification_code = None
            db.session.commit()
            flash("🎓 College email verified. You are now a Verified Student.", "success")
            return redirect(url_for("student.profile"))
        flash("That code does not match. Use the demo code shown at registration, or resend.", "danger")
    return render_template("auth/verify_college.html", profile=profile)


@auth_bp.route("/verify-college/resend", methods=["POST"])
@login_required
def resend_code():
    if not current_user.is_student():
        flash("Only students verify a college email.", "warning")
        return redirect(url_for("main.dashboard_redirect"))
    profile = current_user.student_profile
    if not profile or profile.verified:
        return redirect(url_for("student.profile"))
    import random

    profile.verification_code = f"{random.randint(100000, 999999)}"
    db.session.commit()
    flash(f"New demo verification code: {profile.verification_code}", "success")
    return redirect(url_for("auth.verify_college"))
