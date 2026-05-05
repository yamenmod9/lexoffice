from __future__ import annotations

from flask import Blueprint, g, request

from app.api.common import paginate_query
from app.extensions import db
from app.models import Notification
from app.utils.decorators import auth_required
from app.utils.responses import fail, ok, paginated_meta
from app.utils.serialization import model_to_dict

bp = Blueprint("notifications", __name__, url_prefix="/api/v1/notifications")


@bp.get("/")
@auth_required
def list_notifications():
    query = Notification.query.filter_by(office_id=g.current_user.office_id, user_id=g.current_user.id)

    is_read = request.args.get("is_read")
    if is_read in {"true", "false"}:
        query = query.filter(Notification.is_read == (is_read == "true"))

    ntype = request.args.get("type")
    if ntype:
        query = query.filter(Notification.type == ntype)

    pagination = paginate_query(query.order_by(Notification.created_at.desc()))
    return ok(data=[model_to_dict(item) for item in pagination.items], meta=paginated_meta(pagination))


@bp.put("/<uuid:notification_id>/read")
@auth_required
def mark_read(notification_id):
    notification = Notification.query.filter_by(
        id=notification_id,
        office_id=g.current_user.office_id,
        user_id=g.current_user.id,
    ).first()
    if not notification:
        return fail("NOT_FOUND", "Notification not found", status=404)

    notification.is_read = True
    db.session.commit()
    return ok(data=model_to_dict(notification), message="Notification marked as read")


@bp.put("/read-all")
@auth_required
def mark_all_read():
    Notification.query.filter_by(
        office_id=g.current_user.office_id,
        user_id=g.current_user.id,
        is_read=False,
    ).update({"is_read": True})
    db.session.commit()
    return ok(data={}, message="All notifications marked as read")


@bp.delete("/<uuid:notification_id>")
@auth_required
def delete_notification(notification_id):
    notification = Notification.query.filter_by(
        id=notification_id,
        office_id=g.current_user.office_id,
        user_id=g.current_user.id,
    ).first()
    if not notification:
        return fail("NOT_FOUND", "Notification not found", status=404)

    db.session.delete(notification)
    db.session.commit()
    return ok(data={}, message="Notification deleted")


@bp.get("/unread-count")
@auth_required
def unread_count():
    count = Notification.query.filter_by(
        office_id=g.current_user.office_id,
        user_id=g.current_user.id,
        is_read=False,
    ).count()
    return ok(data={"unread_count": count})
