from __future__ import annotations

from flask import Blueprint, g, request

from app.api.common import load_payload
from app.extensions import db
from app.models import Office, User
from app.models.enums import SubscriptionStatus, UserRole
from app.schemas.core import MemberRoleUpdateSchema, OfficeUpdateSchema, PlanSchema
from app.services.storage_service import upload_file
from app.utils.decorators import auth_required
from app.utils.responses import fail, ok
from app.utils.serialization import model_to_dict

bp = Blueprint("office", __name__, url_prefix="/api/v1/office")


@bp.get("/")
@auth_required
def get_office():
    office = Office.query.filter_by(id=g.current_user.office_id).first()
    return ok(data=model_to_dict(office))


@bp.put("/")
@auth_required
def update_office():
    if g.current_user.role != UserRole.OWNER:
        return fail("FORBIDDEN", "Only owner can update office", status=403)

    payload = load_payload(OfficeUpdateSchema, partial=True)
    office = Office.query.filter_by(id=g.current_user.office_id).first()
    for field, value in payload.items():
        setattr(office, field, value)
    db.session.commit()
    return ok(data=model_to_dict(office), message="Office updated")


@bp.post("/logo")
@auth_required
def upload_logo():
    file = request.files.get("file")
    if not file:
        return fail("VALIDATION_ERROR", "file is required", status=400)

    office = Office.query.filter_by(id=g.current_user.office_id).first()
    file_url, _ = upload_file(file, office.id, "office", office.id)
    office.logo_url = file_url
    db.session.commit()
    return ok(data={"logo_url": file_url})


@bp.get("/members")
@auth_required
def members():
    users = User.query.filter_by(office_id=g.current_user.office_id).order_by(User.created_at.desc()).all()
    return ok(data=[model_to_dict(item, exclude={"password_hash", "mfa_secret"}) for item in users])


@bp.put("/members/<uuid:user_id>")
@auth_required
def update_member(user_id):
    if g.current_user.role != UserRole.OWNER:
        return fail("FORBIDDEN", "Only owner can update roles", status=403)

    payload = load_payload(MemberRoleUpdateSchema)
    member = User.query.filter_by(id=user_id, office_id=g.current_user.office_id, is_active=True).first()
    if not member:
        return fail("NOT_FOUND", "Member not found", status=404)

    member.role = payload["role"]
    db.session.commit()
    return ok(data=model_to_dict(member), message="Member role updated")


@bp.delete("/members/<uuid:user_id>")
@auth_required
def deactivate_member(user_id):
    if g.current_user.role != UserRole.OWNER:
        return fail("FORBIDDEN", "Only owner can deactivate members", status=403)

    member = User.query.filter_by(id=user_id, office_id=g.current_user.office_id, is_active=True).first()
    if not member:
        return fail("NOT_FOUND", "Member not found", status=404)

    member.is_active = False
    db.session.commit()
    return ok(data={}, message="Member deactivated")


@bp.get("/subscription")
@auth_required
def subscription():
    office = Office.query.filter_by(id=g.current_user.office_id).first()
    return ok(
        data={
            "subscription_plan": office.subscription_plan.value if hasattr(office.subscription_plan, "value") else office.subscription_plan,
            "subscription_status": office.subscription_status.value if hasattr(office.subscription_status, "value") else office.subscription_status,
            "trial_ends_at": office.trial_ends_at.isoformat() if office.trial_ends_at else None,
        }
    )


@bp.post("/subscription/upgrade")
@auth_required
def upgrade_subscription():
    if g.current_user.role != UserRole.OWNER:
        return fail("FORBIDDEN", "Only owner can upgrade subscription", status=403)

    payload = load_payload(PlanSchema)
    office = Office.query.filter_by(id=g.current_user.office_id).first()
    office.subscription_plan = payload["subscription_plan"]
    office.subscription_status = SubscriptionStatus.ACTIVE
    db.session.commit()
    return ok(data=model_to_dict(office), message="Subscription upgraded")
