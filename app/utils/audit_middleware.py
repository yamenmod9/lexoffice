from __future__ import annotations

from flask import g, request

from app.extensions import db
from app.models import AuditLog

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def register_audit_middleware(app):
    @app.after_request
    def _audit_after_request(response):
        try:
            if request.method not in WRITE_METHODS:
                return response
            if response.status_code >= 400:
                return response

            user = getattr(g, "current_user", None)
            if not user:
                return response

            payload = request.get_json(silent=True)
            entity_id = payload.get("id") if isinstance(payload, dict) else None

            log = AuditLog(
                office_id=user.office_id,
                user_id=user.id,
                action=request.method,
                entity_type=request.blueprint or "unknown",
                entity_id=entity_id or user.id,
                old_value=None,
                new_value=payload if isinstance(payload, dict) else None,
                ip_address=request.remote_addr,
            )
            db.session.add(log)
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("Failed to write audit log")

        return response
