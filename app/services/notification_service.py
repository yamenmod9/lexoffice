from __future__ import annotations

from datetime import datetime

from flask import current_app
from flask_mail import Message

from app.extensions import db, mail
from app.models import Notification
from app.utils.security import is_quiet_hours

CRITICAL_TYPES = {"appeal_deadline", "critical_appeal_deadlines", "task_overdue"}


_firebase_ready = False


def _init_firebase():
    global _firebase_ready
    if _firebase_ready:
        _firebase_ready = True
        return
    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        current_app.logger.warning("firebase-admin package is not installed; push notifications are disabled")
        return

    if firebase_admin._apps:
        _firebase_ready = True
        return

    credentials_json = current_app.config.get("FIREBASE_CREDENTIALS_JSON")
    if credentials_json:
        cred = credentials.Certificate(credentials_json)
        firebase_admin.initialize_app(cred)
        _firebase_ready = True


def send_email_notification(to_email: str, title: str, body: str):
    if not to_email:
        return False
    try:
        msg = Message(subject=title, recipients=[to_email], body=body)
        mail.send(msg)
        return True
    except Exception:
        current_app.logger.exception("Email notification failed")
        return False


def send_twilio_sms(phone: str, body: str):
    try:
        from twilio.rest import Client as TwilioClient
    except ImportError:
        current_app.logger.warning("twilio package is not installed; SMS notifications are disabled")
        return False

    sid = current_app.config.get("TWILIO_ACCOUNT_SID")
    token = current_app.config.get("TWILIO_AUTH_TOKEN")
    from_number = current_app.config.get("TWILIO_FROM_NUMBER")
    if not sid or not token or not from_number or not phone:
        return False
    try:
        client = TwilioClient(sid, token)
        client.messages.create(from_=from_number, to=phone, body=body)
        return True
    except Exception:
        current_app.logger.exception("SMS notification failed")
        return False


def send_firebase_push(fcm_token: str, title: str, body: str, data: dict | None = None):
    if not fcm_token:
        return False
    try:
        from firebase_admin import messaging
    except ImportError:
        current_app.logger.warning("firebase-admin package is not installed; push notifications are disabled")
        return False

    try:
        _init_firebase()
        if not _firebase_ready:
            return False
        message = messaging.Message(
            token=fcm_token,
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
        )
        messaging.send(message)
        return True
    except Exception:
        current_app.logger.exception("Push notification failed")
        return False


def send_notification(user, ntype: str, title: str, body: str, data: dict | None = None):
    prefs = user.notification_preferences or {}
    channel_pref = prefs.get(ntype, {})
    is_critical = ntype in CRITICAL_TYPES

    in_quiet = is_quiet_hours(user, now=datetime.utcnow())
    if in_quiet and not is_critical:
        record = Notification(
            office_id=user.office_id,
            user_id=user.id,
            type=ntype,
            title=title,
            body=body,
            data=data or {},
            is_read=False,
            sent_push=False,
            sent_email=False,
            sent_sms=False,
        )
        db.session.add(record)
        return record

    sent_push = False
    sent_email = False
    sent_sms = False

    if channel_pref.get("push", True):
        sent_push = send_firebase_push(user.fcm_token, title, body, data)

    if channel_pref.get("email", True):
        sent_email = send_email_notification(user.email, title, body)

    if channel_pref.get("sms", False) and is_critical:
        sent_sms = send_twilio_sms(user.phone, body)

    record = Notification(
        office_id=user.office_id,
        user_id=user.id,
        type=ntype,
        title=title,
        body=body,
        data=data or {},
        is_read=False,
        sent_push=sent_push,
        sent_email=sent_email,
        sent_sms=sent_sms,
    )
    db.session.add(record)
    return record
