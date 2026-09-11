"""Mock escrow only. Never processes real money."""

from datetime import datetime
from extensions import db
from models import Payment, Project


MOCK_NOTE = "Simulated mock escrow — not a real financial transaction."


def create_held_payment(project):
    payment = Payment(
        project_id=project.id,
        amount=project.budget,
        status="Held",
        note=MOCK_NOTE,
    )
    db.session.add(payment)
    return payment


def release_payment(project):
    payment = project.payment
    if not payment:
        return None
    payment.status = "Released"
    payment.released_at = datetime.utcnow()
    payment.note = MOCK_NOTE
    return payment


def request_refund(project):
    payment = project.payment
    if not payment:
        return None
    if payment.status == "Released":
        return None
    payment.status = "Refund Requested"
    payment.note = MOCK_NOTE
    return payment


def refund_payment(project):
    payment = project.payment
    if not payment:
        return None
    payment.status = "Refunded"
    payment.refunded_at = datetime.utcnow()
    payment.note = MOCK_NOTE
    project.status = "REFUNDED"
    return payment
