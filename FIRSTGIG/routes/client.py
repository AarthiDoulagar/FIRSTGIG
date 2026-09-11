from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import Gig, Application, Project, Payment, Dispute, Review
from decorators import role_required

client_bp = Blueprint("client", __name__)


@client_bp.route("/dashboard")
@login_required
@role_required("client")
def dashboard():
    gigs = Gig.query.filter_by(client_id=current_user.id).order_by(Gig.created_at.desc()).all()
    gig_ids = [g.id for g in gigs]
    apps = Application.query.filter(Application.gig_id.in_(gig_ids)).order_by(Application.created_at.desc()).all() if gig_ids else []
    projects = Project.query.filter_by(client_id=current_user.id).order_by(Project.created_at.desc()).all()
    active = [p for p in projects if p.status not in ("COMPLETED", "REFUNDED", "CANCELLED")]
    completed = [p for p in projects if p.status == "COMPLETED"]
    pending_reviews = []
    for p in completed:
        already = any(r.reviewer_id == current_user.id for r in p.reviews)
        if not already:
            pending_reviews.append(p)
    payments = [p.payment for p in projects if p.payment]
    disputes = Dispute.query.join(Project).filter(Project.client_id == current_user.id).all()
    return render_template(
        "client/dashboard.html",
        gigs=gigs,
        applications=apps,
        projects=projects,
        active=active,
        completed=completed,
        pending_reviews=pending_reviews,
        payments=payments,
        disputes=disputes,
    )


@client_bp.route("/profile")
@login_required
@role_required("client")
def profile():
    return render_template("client/profile.html")
