from __future__ import annotations

from flask import request

from app.extensions import db
from app.models import AuditLog


def write_audit_log(
    office_id,
    user_id,
    action: str,
    entity_type: str,
    entity_id,
    old_value=None,
    new_value=None,
):
    log = AuditLog(
        office_id=office_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        ip_address=request.remote_addr,
    )
    db.session.add(log)
