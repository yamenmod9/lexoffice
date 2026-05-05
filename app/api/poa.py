from __future__ import annotations

from datetime import date, timedelta

from flask import Blueprint, g, request

from app.api.common import load_payload
from app.extensions import db
from app.models import PowerOfAttorney
from app.schemas.core import PoaSchema
from app.utils.decorators import require_permission
from app.utils.responses import fail, ok
from app.utils.serialization import model_to_dict

bp = Blueprint("poa", __name__, url_prefix="/api/v1/poa")


@bp.get("/")
@require_permission("clients", "read")
def list_poa():
    query = PowerOfAttorney.query.filter_by(office_id=g.current_user.office_id)

    status = request.args.get("status")
    if status:
        query = query.filter(PowerOfAttorney.status == status)

    client_id = request.args.get("client_id")
    if client_id:
        query = query.filter(PowerOfAttorney.client_id == client_id)

    expiry_before = request.args.get("expiry_before")
    if expiry_before:
        query = query.filter(PowerOfAttorney.expiry_date <= date.fromisoformat(expiry_before))

    items = query.order_by(PowerOfAttorney.created_at.desc()).all()
    return ok(data=[model_to_dict(item) for item in items])


@bp.post("/")
@require_permission("clients", "update")
def create_poa():
    payload = load_payload(PoaSchema)
    item = PowerOfAttorney(office_id=g.current_user.office_id, **payload)
    db.session.add(item)
    db.session.commit()
    return ok(data=model_to_dict(item), status=201)


@bp.get("/<uuid:poa_id>")
@require_permission("clients", "read")
def get_poa(poa_id):
    item = PowerOfAttorney.query.filter_by(id=poa_id, office_id=g.current_user.office_id).first()
    if not item:
        return fail("NOT_FOUND", "POA not found", status=404)
    return ok(data=model_to_dict(item))


@bp.put("/<uuid:poa_id>")
@require_permission("clients", "update")
def update_poa(poa_id):
    item = PowerOfAttorney.query.filter_by(id=poa_id, office_id=g.current_user.office_id).first()
    if not item:
        return fail("NOT_FOUND", "POA not found", status=404)

    payload = load_payload(PoaSchema, partial=True)
    for key, value in payload.items():
        setattr(item, key, value)
    db.session.commit()
    return ok(data=model_to_dict(item), message="POA updated")


@bp.delete("/<uuid:poa_id>")
@require_permission("clients", "update")
def delete_poa(poa_id):
    item = PowerOfAttorney.query.filter_by(id=poa_id, office_id=g.current_user.office_id).first()
    if not item:
        return fail("NOT_FOUND", "POA not found", status=404)

    db.session.delete(item)
    db.session.commit()
    return ok(data={}, message="POA deleted")


@bp.get("/expiring")
@require_permission("clients", "read")
def expiring_poa():
    today = date.today()
    target = today + timedelta(days=30)
    items = (
        PowerOfAttorney.query.filter_by(office_id=g.current_user.office_id)
        .filter(PowerOfAttorney.expiry_date.isnot(None))
        .filter(PowerOfAttorney.expiry_date >= today, PowerOfAttorney.expiry_date <= target)
        .order_by(PowerOfAttorney.expiry_date.asc())
        .all()
    )
    return ok(data=[model_to_dict(item) for item in items])
