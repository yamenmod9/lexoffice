from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pyotp
from flask import current_app

from app.extensions import db
from app.models import ActiveSession, User
from app.services.cache import delete_key, get_json, set_json
from app.utils.security import generate_otp, hash_token


def cache_otp(key: str, otp: str, payload: dict, minutes: int = 10):
    set_json(key, {"otp": otp, "payload": payload}, ex_seconds=minutes * 60)


def validate_cached_otp(key: str, otp: str):
    data = get_json(key)
    if not data:
        return None
    if data.get("otp") != otp:
        return None
    delete_key(key)
    return data.get("payload", {})


def create_session(user: User, refresh_token: str, ip_address: str | None = None, device_name: str | None = None, device_type: str | None = None):
    expires_at = datetime.utcnow() + current_app.config["JWT_REFRESH_TOKEN_EXPIRES"]
    session = ActiveSession(
        user_id=user.id,
        device_name=device_name,
        device_type=device_type,
        ip_address=ip_address,
        refresh_token_hash=hash_token(refresh_token),
        last_active_at=datetime.utcnow(),
        expires_at=expires_at,
    )
    db.session.add(session)
    return session


def revoke_session(user_id, refresh_token: str):
    token_hash = hash_token(refresh_token)
    ActiveSession.query.filter_by(user_id=user_id, refresh_token_hash=token_hash).delete()


def revoke_all_sessions(user_id):
    ActiveSession.query.filter_by(user_id=user_id).delete()


def is_refresh_token_active(user_id, refresh_token: str):
    token_hash = hash_token(refresh_token)
    return (
        ActiveSession.query.filter_by(user_id=user_id, refresh_token_hash=token_hash)
        .filter(ActiveSession.expires_at > datetime.utcnow())
        .first()
        is not None
    )


def generate_mfa_secret():
    return pyotp.random_base32()


def mfa_provisioning_uri(email: str, secret: str, issuer: str = "LexOffice"):
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, code: str):
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def make_client_number(office_id, last_number: int):
    return f"CL-{str(office_id)[:8]}-{last_number + 1:06d}"


def make_invoice_number(last_number: int):
    return f"INV-{last_number + 1:06d}"


def build_invite_token() -> str:
    return f"invite_{uuid4().hex}"


def build_reset_token_key(email: str) -> str:
    return f"otp:reset:{email.lower()}"


def build_register_token_key(email: str) -> str:
    return f"otp:register:{email.lower()}"
