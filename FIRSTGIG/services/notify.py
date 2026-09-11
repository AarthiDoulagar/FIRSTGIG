from datetime import datetime
from extensions import db
from models import Notification, Project


def notify(user_id, message, link=None):
    n = Notification(user_id=user_id, message=message, link=link)
    db.session.add(n)
    return n


def mark_overdue_projects():
    """If the deadline passes and work is not completed, mark OVERDUE (no auto-refund)."""
    open_statuses = ("IN_PROGRESS", "ASSIGNED", "SUBMITTED")
    projects = Project.query.filter(Project.status.in_(open_statuses)).all()
    changed = 0
    for p in projects:
        if p.deadline and p.deadline < datetime.utcnow().date():
            if p.status != "OVERDUE":
                p.status = "OVERDUE"
                notify(p.student_id, f"Project #{p.id} is overdue.", f"/projects/{p.id}")
                notify(p.client_id, f"Project #{p.id} is overdue.", f"/projects/{p.id}")
                changed += 1
    if changed:
        db.session.commit()
    return changed
