from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint, g

from app.api.common import load_payload
from app.extensions import db
from app.models import MemberInvite, Office, User
from app.models.enums import UserRole
from app.schemas.core import AcceptInviteSchema, InviteMemberSchema, PlanSchema, SetupOfficeSchema
from app.services.auth_service import build_invite_token
from app.services.notification_service import send_email_notification
from app.utils.decorators import auth_required
from app.utils.responses import fail, ok
from app.utils.security import hash_password
from app.utils.serialization import model_to_dict

bp = Blueprint("onboarding", __name__, url_prefix="/api/v1/onboarding")


@bp.post("/setup-office")
@auth_required
def setup_office():
    payload = load_payload(SetupOfficeSchema)
    office = Office.query.filter_by(id=g.current_user.office_id).first()
    if not office:
        return fail("NOT_FOUND", "Office not found", status=404)

    for field, value in payload.items():
        setattr(office, field, value)

    db.session.commit()
    return ok(data=model_to_dict(office), message="Office updated")


@bp.post("/choose-plan")
@auth_required
def choose_plan():
    payload = load_payload(PlanSchema)
    office = Office.query.filter_by(id=g.current_user.office_id).first()
    office.subscription_plan = payload["subscription_plan"]
    office.subscription_status = "active"
    db.session.commit()

    payment_intent = f"pi_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return ok(data={"office": model_to_dict(office), "payment_intent": payment_intent})


@bp.post("/invite-member")
@auth_required
def invite_member():
    if g.current_user.role not in {UserRole.OWNER, UserRole.PARTNER}:
        return fail("FORBIDDEN", "Only owner/partner can invite members", status=403)

    payload = load_payload(InviteMemberSchema)
    invites = []
    for email in payload["emails"]:
        token = build_invite_token()
        invite = MemberInvite(
            office_id=g.current_user.office_id,
            email=email.lower(),
            role=payload["role"],
            token=token,
            expires_at=datetime.utcnow() + timedelta(days=3),
            invited_by=g.current_user.id,
        )
        db.session.add(invite)
        invites.append(invite)
        accept_link = f"https://app.lexoffice.local/invite/accept?token={token}"
        send_email_notification(email, "LexOffice invite", f"Accept your invite: {accept_link}")

    db.session.commit()
    return ok(data=[model_to_dict(item) for item in invites], message="Invites sent")


@bp.post("/accept-invite")
def accept_invite():
    payload = load_payload(AcceptInviteSchema)

    invite = MemberInvite.query.filter_by(token=payload["token"], accepted=False).first()
    if not invite or invite.expires_at < datetime.utcnow():
        return fail("INVALID_INVITE", "Invite is invalid or expired", status=400)

    existing = User.query.filter_by(email=invite.email).first()
    if existing:
        return fail("EMAIL_EXISTS", "Email already in use", status=409)

    user = User(
        office_id=invite.office_id,
        full_name=payload["full_name"],
        email=invite.email,
        phone=payload["phone"],
        password_hash=hash_password(payload["password"]),
        role=invite.role,
        notification_preferences={},
    )
    invite.accepted = True
    db.session.add(user)
    db.session.commit()

    return ok(data=model_to_dict(user), message="Invite accepted")
