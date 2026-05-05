from app.extensions import db
from app.models import Notification
from app.models.enums import UserRole


def test_notification_endpoints(client, make_user, auth_headers):
    office, owner = make_user("notif-owner@example.com", role=UserRole.OWNER)

    n = Notification(
        office_id=owner.office_id,
        user_id=owner.id,
        type="session_reminder",
        title="Test",
        body="Body",
        data={},
    )
    db.session.add(n)
    db.session.commit()

    listed = client.get("/api/v1/notifications/", headers=auth_headers(owner))
    assert listed.status_code == 200
    assert listed.json["meta"]["total"] >= 1

    unread = client.get("/api/v1/notifications/unread-count", headers=auth_headers(owner))
    assert unread.status_code == 200
    assert unread.json["data"]["unread_count"] >= 1

    mark = client.put(f"/api/v1/notifications/{n.id}/read", headers=auth_headers(owner))
    assert mark.status_code == 200

    mark_all = client.put("/api/v1/notifications/read-all", headers=auth_headers(owner))
    assert mark_all.status_code == 200
