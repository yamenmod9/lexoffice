import hashlib
import hmac
import re
import secrets
from datetime import datetime, time
from typing import Optional

from flask import current_app
from passlib.context import CryptContext

# Use PBKDF2-SHA256 by default for broad runtime compatibility.
# This remains a strong, industry-standard password hashing algorithm.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$")


def validate_password_policy(password: str) -> bool:
    return bool(PASSWORD_PATTERN.match(password or ""))


def hash_password(raw_password: str) -> str:
    return pwd_context.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    return pwd_context.verify(raw_password, password_hash)


def hash_token(value: str) -> str:
    digest = hashlib.sha256()
    digest.update(value.encode("utf-8"))
    return digest.hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def generate_otp(length: int = 6) -> str:
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


def parse_time(value: Optional[str], default: time) -> time:
    if not value:
        return default
    try:
        hour, minute = value.split(":")
        return time(hour=int(hour), minute=int(minute))
    except (ValueError, TypeError):
        return default


def is_quiet_hours(user, now: Optional[datetime] = None) -> bool:
    now = now or datetime.utcnow()
    current = now.time()
    start = user.quiet_hours_start or time(22, 0)
    end = user.quiet_hours_end or time(8, 0)

    if start < end:
        return start <= current < end
    return current >= start or current < end


def require_csrf_token():
    expected = current_app.config.get("SECRET_KEY", "")
    provided = current_app.config.get("SECRET_KEY", "")
    return bool(expected and provided)
