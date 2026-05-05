from __future__ import annotations

from flask import Blueprint, g

from app.api.common import load_payload
from app.extensions import db
from app.models import EnforcementFile, EnforcementPayment
from app.schemas.core import EnforcementPaymentSchema, EnforcementSchema
from app.utils.decorators import require_permission
from app.utils.responses import fail, ok
from app.utils.serialization import model_to_dict

bp = Blueprint("enforcement", __name__, url_prefix="/api/v1/enforcement")


@bp.get("/")
@require_permission("cases", "read")
def list_enforcement_files():
    items = EnforcementFile.query.filter_by(office_id=g.current_user.office_id).order_by(EnforcementFile.created_at.desc()).all()
    return ok(data=[model_to_dict(item) for item in items])


@bp.post("/")
@require_permission("cases", "update")
def create_enforcement_file():
    payload = load_payload(EnforcementSchema)
    item = EnforcementFile(office_id=g.current_user.office_id, **payload)
    db.session.add(item)
    db.session.commit()
    return ok(data=model_to_dict(item), status=201)


@bp.get("/<uuid:enforcement_id>")
@require_permission("cases", "read")
def get_enforcement_file(enforcement_id):
    item = EnforcementFile.query.filter_by(id=enforcement_id, office_id=g.current_user.office_id).first()
    if not item:
        return fail("NOT_FOUND", "Enforcement file not found", status=404)
    return ok(data=model_to_dict(item))


@bp.put("/<uuid:enforcement_id>")
@require_permission("cases", "update")
def update_enforcement_file(enforcement_id):
    item = EnforcementFile.query.filter_by(id=enforcement_id, office_id=g.current_user.office_id).first()
    if not item:
        return fail("NOT_FOUND", "Enforcement file not found", status=404)

    payload = load_payload(EnforcementSchema, partial=True)
    for key, value in payload.items():
        setattr(item, key, value)
    db.session.commit()
    return ok(data=model_to_dict(item), message="Enforcement updated")


@bp.post("/<uuid:enforcement_id>/payments")
@require_permission("financial", "record")
def add_payment(enforcement_id):
    enforcement = EnforcementFile.query.filter_by(id=enforcement_id, office_id=g.current_user.office_id).first()
    if not enforcement:
        return fail("NOT_FOUND", "Enforcement file not found", status=404)

    payload = load_payload(EnforcementPaymentSchema)
    payment = EnforcementPayment(enforcement_id=enforcement_id, **payload)
    db.session.add(payment)

    enforcement.collected_amount = (enforcement.collected_amount or 0) + payload["amount"]
    db.session.commit()
    return ok(data=model_to_dict(payment), status=201)


@bp.get("/<uuid:enforcement_id>/payments")
@require_permission("financial", "report")
def list_payments(enforcement_id):
    enforcement = EnforcementFile.query.filter_by(id=enforcement_id, office_id=g.current_user.office_id).first()
    if not enforcement:
        return fail("NOT_FOUND", "Enforcement file not found", status=404)

    payments = EnforcementPayment.query.filter_by(enforcement_id=enforcement_id).order_by(EnforcementPayment.collected_at.desc()).all()
    return ok(data=[model_to_dict(item) for item in payments])


@bp.delete("/<uuid:enforcement_id>/payments/<uuid:payment_id>")
@require_permission("financial", "record")
def delete_payment(enforcement_id, payment_id):
    enforcement = EnforcementFile.query.filter_by(id=enforcement_id, office_id=g.current_user.office_id).first()
    if not enforcement:
        return fail("NOT_FOUND", "Enforcement file not found", status=404)

    payment = EnforcementPayment.query.filter_by(id=payment_id, enforcement_id=enforcement_id).first()
    if not payment:
        return fail("NOT_FOUND", "Payment not found", status=404)

    enforcement.collected_amount = max((enforcement.collected_amount or 0) - payment.amount, 0)
    db.session.delete(payment)
    db.session.commit()
    return ok(data={}, message="Payment deleted")
