from __future__ import annotations

from datetime import time

from flask import Blueprint, g, request

from app.api.common import load_payload
from app.extensions import db
from app.schemas.core import (
    NotificationPrefSchema,
    PasswordChangeSchema,
    QuietHoursSchema,
    UserProfileUpdateSchema,
)
from app.services.storage_service import upload_file
from app.utils.decorators import auth_required
from app.utils.responses import fail, ok
from app.utils.security import parse_time, validate_password_policy, verify_password, hash_password
from app.utils.serialization import model_to_dict

bp = Blueprint("users", __name__, url_prefix="/api/v1/users")


@bp.get("/me")
@auth_required
def me():
    return ok(data=model_to_dict(g.current_user, exclude={"password_hash", "mfa_secret"}))


@bp.put("/me")
@auth_required
def update_me():
    payload = load_payload(UserProfileUpdateSchema, partial=True)
    for field, value in payload.items():
        setattr(g.current_user, field, value)
    db.session.commit()
    return ok(data=model_to_dict(g.current_user, exclude={"password_hash", "mfa_secret"}))


@bp.post("/me/avatar")
@auth_required
def upload_avatar():
    file = request.files.get("file")
    if not file:
        return fail("VALIDATION_ERROR", "file is required", status=400)

    file_url, _ = upload_file(file, g.current_user.office_id, "user", g.current_user.id)
    g.current_user.profile_picture_url = file_url
    db.session.commit()
    return ok(data={"profile_picture_url": file_url})


@bp.put("/me/password")
@auth_required
def change_password():
    payload = load_payload(PasswordChangeSchema)
    if not verify_password(payload["old_password"], g.current_user.password_hash):
        return fail("INVALID_PASSWORD", "Old password is incorrect", status=400)

    if not validate_password_policy(payload["new_password"]):
        return fail(
            "WEAK_PASSWORD",
            "Password must be min 8 chars and include uppercase, number, symbol",
            status=400,
        )

    g.current_user.password_hash = hash_password(payload["new_password"])
    db.session.commit()
    return ok(data={}, message="Password updated")


@bp.put("/me/notification-preferences")
@auth_required
def update_notification_preferences():
    payload = load_payload(NotificationPrefSchema)
    g.current_user.notification_preferences = payload["preferences"]
    db.session.commit()
    return ok(data={"notification_preferences": g.current_user.notification_preferences})


@bp.put("/me/quiet-hours")
@auth_required
def set_quiet_hours():
    payload = load_payload(QuietHoursSchema)
    g.current_user.quiet_hours_start = parse_time(payload["quiet_hours_start"], time(22, 0))
    g.current_user.quiet_hours_end = parse_time(payload["quiet_hours_end"], time(8, 0))
    db.session.commit()
    return ok(
        data={
            "quiet_hours_start": g.current_user.quiet_hours_start.isoformat(),
            "quiet_hours_end": g.current_user.quiet_hours_end.isoformat(),
        }
    )
