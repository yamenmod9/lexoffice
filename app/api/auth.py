from __future__ import annotations

import base64
from datetime import datetime, timedelta
from io import BytesIO

import qrcode
from flask import Blueprint, g, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
)

from app.api.common import load_payload
from app.extensions import db, limiter
from app.models import ActiveSession, Office, User
from app.models.enums import UserRole
from app.schemas.core import (
    ForgotPasswordSchema,
    LoginSchema,
    RefreshSchema,
    RegisterSchema,
    ResetPasswordSchema,
    VerifyOtpSchema,
)
from app.services.auth_service import (
    build_register_token_key,
    build_reset_token_key,
    cache_otp,
    create_session,
    generate_mfa_secret,
    is_refresh_token_active,
    mfa_provisioning_uri,
    revoke_all_sessions,
    revoke_session,
    validate_cached_otp,
    verify_totp,
)
from app.services.cache import delete_key, get_json, set_json
from app.services.notification_service import send_email_notification
from app.utils.decorators import auth_required
from app.utils.helpers import parse_uuid
from app.utils.responses import fail, ok
from app.utils.security import generate_otp, hash_password, validate_password_policy, verify_password
from app.utils.serialization import model_to_dict

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@bp.post("/register")
@limiter.limit("5 per minute")
def register():
    payload = load_payload(RegisterSchema)

    if User.query.filter_by(email=payload["email"].lower()).first():
        return fail("EMAIL_EXISTS", "Email already registered", status=409)

    if not validate_password_policy(payload["password"]):
        return fail(
            "WEAK_PASSWORD",
            "Password must be min 8 chars and include uppercase, number, symbol",
            status=400,
        )

    otp = generate_otp()
    cache_key = build_register_token_key(payload["email"])
    cache_otp(cache_key, otp, payload, minutes=10)

    send_email_notification(
        payload["email"],
        "LexOffice registration OTP",
        f"Your verification code is: {otp}",
    )

    return ok(
        data={"otp_expires_in_seconds": 600},
        message="OTP sent to email",
        status=201,
    )


@bp.post("/verify-otp")
@limiter.limit("3 per minute")
def verify_otp():
    payload = load_payload(VerifyOtpSchema)
    cache_key = build_register_token_key(payload["email"])
    register_payload = validate_cached_otp(cache_key, payload["otp"])

    if not register_payload:
        return fail("INVALID_OTP", "Invalid or expired OTP", status=400)

    if User.query.filter_by(email=register_payload["email"].lower()).first():
        return fail("EMAIL_EXISTS", "Email already registered", status=409)

    office = Office(
        name=register_payload["office_name"],
        official_email=register_payload["email"].lower(),
        official_phone=register_payload["phone"],
        subscription_status="trial",
        trial_ends_at=datetime.utcnow() + timedelta(days=14),
    )
    db.session.add(office)
    db.session.flush()

    user = User(
        office_id=office.id,
        full_name=register_payload["full_name"],
        email=register_payload["email"].lower(),
        phone=register_payload["phone"],
        password_hash=hash_password(register_payload["password"]),
        role=UserRole.OWNER,
        notification_preferences={},
    )
    db.session.add(user)
    db.session.commit()

    return ok(data={"office": model_to_dict(office), "owner": model_to_dict(user)})


@bp.post("/login")
@limiter.limit("5 per minute")
def login():
    payload = load_payload(LoginSchema)
    user = User.query.filter_by(email=payload["email"].lower(), is_active=True).first()

    if not user or not verify_password(payload["password"], user.password_hash):
        return fail("INVALID_CREDENTIALS", "Invalid email or password", status=401)

    if user.mfa_enabled:
        mfa_code = payload.get("mfa_code")
        if not mfa_code or not user.mfa_secret or not verify_totp(user.mfa_secret, mfa_code):
            return fail("MFA_REQUIRED", "MFA code is required or invalid", status=401)

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"office_id": str(user.office_id), "role": user.role.value},
    )
    refresh_token = create_refresh_token(identity=str(user.id))

    create_session(
        user,
        refresh_token,
        ip_address=request.remote_addr,
        device_name=payload.get("device_name"),
        device_type=payload.get("device_type"),
    )

    user.last_login_at = datetime.utcnow()
    db.session.commit()

    return ok(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": model_to_dict(user),
        }
    )


@bp.post("/refresh")
def refresh():
    payload = load_payload(RefreshSchema)
    refresh_token = payload["refresh_token"]

    try:
        token_data = decode_token(refresh_token)
    except Exception:
        return fail("INVALID_TOKEN", "Invalid refresh token", status=401)

    if token_data.get("type") != "refresh":
        return fail("INVALID_TOKEN_TYPE", "Refresh token required", status=401)

    user = User.query.filter_by(id=parse_uuid(token_data.get("sub")), is_active=True).first()
    if not user:
        return fail("UNAUTHORIZED", "Invalid user", status=401)

    if not is_refresh_token_active(user.id, refresh_token):
        return fail("SESSION_EXPIRED", "Session expired", status=401)

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"office_id": str(user.office_id), "role": user.role.value},
    )
    return ok(data={"access_token": access_token})


@bp.post("/logout")
@auth_required
def logout():
    payload = request.get_json(silent=True) or {}
    refresh_token = payload.get("refresh_token")
    if refresh_token:
        revoke_session(g.current_user.id, refresh_token)
        db.session.commit()
    return ok(data={}, message="Logged out")


@bp.post("/logout-all")
@auth_required
def logout_all():
    revoke_all_sessions(g.current_user.id)
    db.session.commit()
    return ok(data={}, message="All sessions revoked")


@bp.post("/forgot-password")
def forgot_password():
    payload = load_payload(ForgotPasswordSchema)
    user = User.query.filter_by(email=payload["email"].lower(), is_active=True).first()
    if not user:
        return ok(data={}, message="If account exists, OTP was sent")

    otp = generate_otp()
    cache_otp(build_reset_token_key(user.email), otp, {"user_id": str(user.id)}, minutes=10)
    send_email_notification(user.email, "LexOffice password reset OTP", f"OTP: {otp}")
    return ok(data={"otp_expires_in_seconds": 600}, message="OTP sent")


@bp.post("/reset-password")
def reset_password():
    payload = load_payload(ResetPasswordSchema)

    if not validate_password_policy(payload["new_password"]):
        return fail(
            "WEAK_PASSWORD",
            "Password must be min 8 chars and include uppercase, number, symbol",
            status=400,
        )

    data = validate_cached_otp(build_reset_token_key(payload["email"]), payload["otp"])
    if not data:
        return fail("INVALID_OTP", "Invalid or expired OTP", status=400)

    user = User.query.filter_by(id=parse_uuid(data["user_id"]), is_active=True).first()
    if not user:
        return fail("UNAUTHORIZED", "User not found", status=404)

    user.password_hash = hash_password(payload["new_password"])
    revoke_all_sessions(user.id)
    db.session.commit()
    return ok(data={}, message="Password reset successful")


@bp.post("/mfa/enable")
@auth_required
def mfa_enable():
    secret = generate_mfa_secret()
    key = f"mfa:pending:{g.current_user.id}"
    set_json(key, {"secret": secret}, ex_seconds=600)

    uri = mfa_provisioning_uri(g.current_user.email, secret)
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    stream = BytesIO()
    img.save(stream, format="PNG")
    qr_data = base64.b64encode(stream.getvalue()).decode("utf-8")

    return ok(
        data={
            "secret": secret,
            "provisioning_uri": uri,
            "qr_png_base64": qr_data,
        }
    )


@bp.post("/mfa/verify")
@auth_required
def mfa_verify():
    payload = request.get_json(silent=True) or {}
    code = payload.get("code")
    if not code:
        return fail("VALIDATION_ERROR", "code is required", status=400)

    key = f"mfa:pending:{g.current_user.id}"
    data = get_json(key)
    if not data:
        return fail("MFA_SETUP_EXPIRED", "MFA setup expired", status=400)

    secret = data.get("secret")
    if not verify_totp(secret, code):
        return fail("INVALID_MFA_CODE", "Invalid MFA code", status=400)

    g.current_user.mfa_secret = secret
    g.current_user.mfa_enabled = True
    delete_key(key)
    db.session.commit()
    return ok(data={}, message="MFA enabled")


@bp.post("/mfa/disable")
@auth_required
def mfa_disable():
    payload = request.get_json(silent=True) or {}
    confirm_password = payload.get("password")

    if not confirm_password:
        return fail("VALIDATION_ERROR", "password is required", status=400)

    if g.current_user.role == UserRole.OWNER and not verify_password(confirm_password, g.current_user.password_hash):
        return fail("INVALID_PASSWORD", "Password confirmation failed", status=400)

    g.current_user.mfa_enabled = False
    g.current_user.mfa_secret = None
    db.session.commit()
    return ok(data={}, message="MFA disabled")


@bp.get("/sessions")
@auth_required
def list_sessions():
    sessions = (
        ActiveSession.query.filter_by(user_id=g.current_user.id)
        .order_by(ActiveSession.last_active_at.desc())
        .all()
    )
    return ok(data=[model_to_dict(item) for item in sessions])


@bp.delete("/sessions/<uuid:session_id>")
@auth_required
def terminate_session(session_id):
    session_obj = ActiveSession.query.filter_by(id=session_id, user_id=g.current_user.id).first()
    if not session_obj:
        return fail("NOT_FOUND", "Session not found", status=404)

    db.session.delete(session_obj)
    db.session.commit()
    return ok(data={}, message="Session terminated")
