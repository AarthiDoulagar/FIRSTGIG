from extensions import db
from models import Project, Review, StudentProfile, ClientProfile


def _safe_pct(part, whole):
    if not whole:
        return 100.0
    return round((part / whole) * 100.0, 1)


def recalculate_student(student_user_id):
    """Reliability is performance-based, not the same as star rating."""
    profile = StudentProfile.query.filter_by(user_id=student_user_id).first()
    if not profile:
        return

    projects = Project.query.filter_by(student_id=student_user_id).all()
    completed = [p for p in projects if p.status == "COMPLETED"]
    cancelled = [p for p in projects if p.status in ("CANCELLED", "REFUNDED")]
    disputed = [p for p in projects if p.status == "DISPUTED"]
    finished = [p for p in projects if p.status in ("COMPLETED", "CANCELLED", "REFUNDED")]

    on_time = 0
    for p in completed:
        if p.completed_at and p.deadline:
            on_time += int(p.completed_at.date() <= p.deadline)

    ratings = [
        r.rating
        for r in Review.query.filter_by(reviewed_user_id=student_user_id).all()
        if r.reviewer_id != student_user_id
    ]

    profile.completed_gigs = len(completed)
    profile.on_time_percentage = _safe_pct(on_time, len(completed)) if completed else 100.0
    profile.dispute_count = len(disputed) + len([p for p in projects if p.disputes])
    # unique dispute projects
    profile.dispute_count = len({p.id for p in projects if p.disputes})
    profile.cancellation_count = len(cancelled)
    profile.rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0

    completion_rate = _safe_pct(len(completed), len(finished)) if finished else 100.0
    rating_pct = (profile.rating / 5.0) * 100 if profile.rating else 70.0
    dispute_rate = (profile.dispute_count / max(len(projects), 1)) * 100
    cancel_rate = (profile.cancellation_count / max(len(projects), 1)) * 100

    score = (
        profile.on_time_percentage * 0.35
        + completion_rate * 0.30
        + rating_pct * 0.20
        + max(0, 100 - dispute_rate * 4) * 0.10
        + max(0, 100 - cancel_rate * 3) * 0.05
    )
    profile.reliability_score = round(min(100, max(20, score)), 1)
    db.session.commit()


def recalculate_client(client_user_id):
    profile = ClientProfile.query.filter_by(user_id=client_user_id).first()
    if not profile:
        return
    ratings = [
        r.rating
        for r in Review.query.filter_by(reviewed_user_id=client_user_id).all()
        if r.reviewer_id != client_user_id
    ]
    profile.rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
    db.session.commit()
