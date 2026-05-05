from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

celery = Celery("lexoffice")


def make_celery(flask_app):
    celery.conf.update(
        broker_url=flask_app.config["CELERY_BROKER_URL"],
        result_backend=flask_app.config["CELERY_RESULT_BACKEND"],
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Africa/Cairo",
        enable_utc=True,
        beat_schedule={
            "session-reminders-every-30m": {
                "task": "app.tasks.jobs.session_reminders",
                "schedule": 1800,
            },
            "appeal-deadline-reminders": {
                "task": "app.tasks.jobs.appeal_deadline_reminders",
                "schedule": crontab(hour=9, minute=0),
            },
            "poa-expiry-reminders": {
                "task": "app.tasks.jobs.poa_expiry_reminders",
                "schedule": crontab(hour=9, minute=0),
            },
            "task-overdue-checker": {
                "task": "app.tasks.jobs.task_overdue_checker",
                "schedule": 3600,
            },
            "invoice-overdue-checker": {
                "task": "app.tasks.jobs.invoice_overdue_checker",
                "schedule": crontab(hour=10, minute=0),
            },
            "daily-digest": {
                "task": "app.tasks.jobs.daily_digest",
                "schedule": crontab(hour=7, minute=30),
            },
            "poa-status-updater": {
                "task": "app.tasks.jobs.poa_status_updater",
                "schedule": crontab(hour=0, minute=0),
            },
            "audit-cleanup": {
                "task": "app.tasks.jobs.audit_cleanup",
                "schedule": crontab(day_of_month=1, hour=2, minute=0),
            },
        },
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


def get_celery():
    return celery
