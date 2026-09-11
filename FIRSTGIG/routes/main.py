from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from extensions import db
from models import Notification
from services.level_service import level_for_completed, LEVELS
from services.recommendation_service import recommend_gigs
from models import Project, Application, Gig, Payment, Dispute, Review

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html", levels=LEVELS)


@main_bp.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html", levels=LEVELS)


@main_bp.route("/go")
@login_required
def dashboard_redirect():
    if current_user.role == "admin":
        return redirect(url_for("admin.dashboard"))
    if current_user.role == "client":
        return redirect(url_for("client.dashboard"))
    return redirect(url_for("student.dashboard"))


@main_bp.route("/notifications")
@login_required
def notifications():
    items = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    for n in items:
        n.is_read = True
    db.session.commit()
    return render_template("notifications.html", items=items)
