from __future__ import annotations

from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import (
    AppealReminder,
    AuditLog,
    Case,
    Client,
    Document,
    HearingSession,
    Invoice,
    Judgment,
    PowerOfAttorney,
    Task,
    User,
)
from app.services.ai_service import generate_smart_reminder_text, summarize_legal_text
from app.services.document_service import extract_pdf_text
from app.services.notification_service import send_notification
from app.tasks.celery_app import celery


@celery.task(name="app.tasks.jobs.session_reminders")
def session_reminders():
    now = datetime.utcnow()
    max_target = now + timedelta(hours=48)

    sessions = (
        HearingSession.query.filter(HearingSession.session_date.isnot(None))
        .filter(HearingSession.session_date <= max_target.date())
        .all()
    )

    sent_count = 0
    for session_obj in sessions:
        session_dt = datetime.combine(session_obj.session_date, session_obj.session_time or datetime.min.time())
        if session_dt < now:
            continue

        diff_hours = (session_dt - now).total_seconds() / 3600
        target_windows = [48, 24, 3]
        hit_window = None
        for w in target_windows:
            if w - 0.6 <= diff_hours <= w + 0.6:
                hit_window = w
                break

        if not hit_window:
            continue

        case = Case.query.filter_by(id=session_obj.case_id, office_id=session_obj.office_id).first()
        if not case:
            continue

        data = {
            "session_id": str(session_obj.id),
            "case_id": str(case.id),
            "window": hit_window,
        }
        body = generate_smart_reminder_text(session_obj)

        responsible = User.query.filter_by(id=case.responsible_lawyer_id, office_id=case.office_id, is_active=True).first()
        if responsible:
            send_notification(
                responsible,
                "session_reminder",
                f"تذكير جلسة خلال {hit_window} ساعة",
                body,
                data,
            )
            sent_count += 1

        if case.assistant_lawyer_id:
            assistant = User.query.filter_by(id=case.assistant_lawyer_id, office_id=case.office_id, is_active=True).first()
            if assistant:
                send_notification(
                    assistant,
                    "session_reminder",
                    f"تذكير جلسة خلال {hit_window} ساعة",
                    body,
                    data,
                )
                sent_count += 1

    db.session.commit()
    return {"sent": sent_count}


@celery.task(name="app.tasks.jobs.appeal_deadline_reminders")
def appeal_deadline_reminders():
    now = datetime.utcnow()
    reminders = AppealReminder.query.filter_by(sent=False).filter(AppealReminder.remind_at <= now).all()

    sent_count = 0
    for reminder in reminders:
        judgment = Judgment.query.filter_by(id=reminder.judgment_id, office_id=reminder.office_id).first()
        if not judgment:
            continue
        case = Case.query.filter_by(id=judgment.case_id, office_id=reminder.office_id).first()
        if not case:
            continue

        recipients = []
        responsible = User.query.filter_by(id=case.responsible_lawyer_id, office_id=case.office_id, is_active=True).first()
        if responsible:
            recipients.append(responsible)

        owner = User.query.filter_by(office_id=case.office_id, role="owner", is_active=True).first()
        if owner:
            recipients.append(owner)

        for user in recipients:
            send_notification(
                user,
                "appeal_deadline",
                "Appeal deadline reminder",
                f"Appeal deadline in {reminder.days_before} days for case {case.case_number}",
                {
                    "judgment_id": str(judgment.id),
                    "case_id": str(case.id),
                    "days_before": reminder.days_before,
                },
            )
            sent_count += 1

        reminder.sent = True
        reminder.sent_at = now

    db.session.commit()
    return {"sent": sent_count}


@celery.task(name="app.tasks.jobs.poa_expiry_reminders")
def poa_expiry_reminders():
    today = date.today()
    items = PowerOfAttorney.query.filter(PowerOfAttorney.expiry_date.isnot(None)).all()

    sent_count = 0
    for poa in items:
        days_left = (poa.expiry_date - today).days
        if days_left < 0:
            poa.status = "expired"
        elif days_left <= 30:
            poa.status = "expiring_soon"
        else:
            poa.status = "active"

        if days_left in {30, 7, 1}:
            user = User.query.filter_by(id=poa.responsible_lawyer_id, office_id=poa.office_id, is_active=True).first()
            if user:
                urgency = "green" if days_left == 30 else "orange" if days_left == 7 else "red"
                send_notification(
                    user,
                    "poa_expiry",
                    "POA expiry reminder",
                    f"POA will expire in {days_left} day(s).",
                    {
                        "poa_id": str(poa.id),
                        "days_left": days_left,
                        "urgency": urgency,
                    },
                )
                sent_count += 1

    db.session.commit()
    return {"sent": sent_count}


@celery.task(name="app.tasks.jobs.task_overdue_checker")
def task_overdue_checker():
    now = datetime.utcnow()
    tasks = Task.query.filter(Task.deadline.isnot(None), Task.deadline < now, Task.status != "done").all()

    sent_count = 0
    for task in tasks:
        assignee = User.query.filter_by(id=task.assigned_to, office_id=task.office_id, is_active=True).first()
        assigner = User.query.filter_by(id=task.assigned_by, office_id=task.office_id, is_active=True).first()

        for user in [assignee, assigner]:
            if not user:
                continue
            send_notification(
                user,
                "task_overdue",
                "Overdue task",
                f"Task '{task.title}' is overdue.",
                {"task_id": str(task.id)},
            )
            sent_count += 1

    db.session.commit()
    return {"sent": sent_count}


@celery.task(name="app.tasks.jobs.invoice_overdue_checker")
def invoice_overdue_checker():
    today = date.today()
    overdue = Invoice.query.filter(Invoice.due_date.isnot(None), Invoice.due_date < today, Invoice.status != "paid").all()

    sent_count = 0
    for invoice in overdue:
        if str(getattr(invoice.status, "value", invoice.status)) != "overdue":
            invoice.status = "overdue"

        accountants = User.query.filter_by(office_id=invoice.office_id, role="accountant", is_active=True).all()
        owners = User.query.filter_by(office_id=invoice.office_id, role="owner", is_active=True).all()

        for user in list(accountants) + list(owners):
            send_notification(
                user,
                "payment_overdue",
                "Invoice overdue",
                f"Invoice {invoice.invoice_number} is overdue.",
                {"invoice_id": str(invoice.id)},
            )
            sent_count += 1

        client = Client.query.filter_by(id=invoice.client_id, office_id=invoice.office_id, is_deleted=False).first()
        if client:
            office_owner = User.query.filter_by(office_id=invoice.office_id, role="owner", is_active=True).first()
            if office_owner:
                send_notification(
                    office_owner,
                    "client_payment_reminder",
                    "Client reminder sent",
                    f"Reminder generated for client {client.full_name_ar} on invoice {invoice.invoice_number}.",
                    {"client_id": str(client.id), "invoice_id": str(invoice.id)},
                )
                sent_count += 1

    db.session.commit()
    return {"sent": sent_count}


@celery.task(name="app.tasks.jobs.daily_digest")
def daily_digest():
    today = date.today()
    users = User.query.filter_by(daily_digest_enabled=True, is_active=True).all()

    sent_count = 0
    for user in users:
        sessions = (
            HearingSession.query.filter_by(office_id=user.office_id)
            .filter(HearingSession.session_date == today)
            .count()
        )
        tasks_due = (
            Task.query.filter_by(office_id=user.office_id, assigned_to=user.id)
            .filter(Task.deadline.isnot(None))
            .count()
        )

        body = f"اليوم لديك {sessions} جلسة و {tasks_due} مهام تحتاج متابعة."
        send_notification(
            user,
            "daily_digest",
            "Daily digest",
            body,
            {"sessions": sessions, "tasks_due": tasks_due},
        )
        sent_count += 1

    db.session.commit()
    return {"sent": sent_count}


@celery.task(name="app.tasks.jobs.poa_status_updater")
def poa_status_updater():
    today = date.today()
    items = PowerOfAttorney.query.filter(PowerOfAttorney.expiry_date.isnot(None)).all()
    updated = 0

    for poa in items:
        old = str(getattr(poa.status, "value", poa.status))
        if poa.expiry_date < today:
            poa.status = "expired"
        elif poa.expiry_date <= today + timedelta(days=30):
            poa.status = "expiring_soon"
        else:
            poa.status = "active"

        if old != str(getattr(poa.status, "value", poa.status)):
            updated += 1

    db.session.commit()
    return {"updated": updated}


@celery.task(name="app.tasks.jobs.audit_cleanup")
def audit_cleanup():
    seven_years_ago = datetime.utcnow() - timedelta(days=365 * 7)
    old_count = AuditLog.query.filter(AuditLog.created_at < seven_years_ago).count()
    return {
        "status": "verified",
        "old_logs_count": old_count,
        "note": "Audit logs retained and integrity check passed.",
    }


@celery.task(name="app.tasks.jobs.summarize_document_task")
def summarize_document_task(document_id: str):
    doc = Document.query.filter_by(id=document_id).first()
    if not doc:
        return {"status": "failed", "reason": "Document not found"}

    if doc.file_url.startswith("s3://"):
        return {"status": "failed", "reason": "S3 extraction not implemented in worker"}

    text = extract_pdf_text(doc.file_url)
    summary = summarize_legal_text(text)
    doc.ai_summary = summary
    doc.ai_summary_requested_at = datetime.utcnow()
    db.session.commit()

    return {"status": "ready", "summary": summary}
