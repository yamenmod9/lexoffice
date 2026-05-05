from __future__ import annotations

from functools import wraps
from http import HTTPStatus

from flask import g
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from app.models import User
from app.services.rbac import has_permission
from app.utils.helpers import parse_uuid
from app.utils.responses import fail


def get_current_user() -> User | None:
    identity = get_jwt_identity()
    identity_uuid = parse_uuid(identity)
    if not identity_uuid:
        return None
    return User.query.filter_by(id=identity_uuid, is_active=True).first()


def auth_required(fn):
    @jwt_required()
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return fail("UNAUTHORIZED", "Invalid or inactive user", status=HTTPStatus.UNAUTHORIZED)
        g.current_user = user
        g.jwt_claims = get_jwt()
        return fn(*args, **kwargs)

    return wrapper


def require_permission(resource: str, action: str):
    permission_key = f"{resource}.{action}"

    def decorator(fn):
        @auth_required
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = g.current_user
            decision = has_permission(user.role.value if hasattr(user.role, "value") else user.role, permission_key)
            if not decision.allowed:
                return fail(
                    "FORBIDDEN",
                    "Insufficient permissions",
                    status=HTTPStatus.FORBIDDEN,
                )
            g.permission_scope = decision.scope
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def office_scoped_query(model):
    user = g.current_user
    if hasattr(model, "office_id"):
        return model.query.filter_by(office_id=user.office_id)
    return model.query


def enforce_scope_owner(query, user, owner_field: str):
    scope = getattr(g, "permission_scope", "all")
    if scope == "own":
        return query.filter(getattr(query.column_descriptions[0]["entity"], owner_field) == user.id)
    if scope == "team":
        return query
    if scope in {"all", "financial", "print_only"}:
        return query
    return query
