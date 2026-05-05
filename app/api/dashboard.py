from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from flask import Blueprint, g
from sqlalchemy import func

from app.models import AppealReminder, Case, Client, HearingSession, Invoice, Judgment, Payment, PowerOfAttorney, Task
from app.utils.decorators import auth_required
from app.utils.responses import ok
from app.utils.serialization import model_to_dict

bp = Blueprint("dashboard", __name__, url_prefix="/api/v1/dashboard")


@bp.get("/summary")
@auth_required
def summary():
    office_id = g.current_user.office_id
    today = date.today()

    active_cases_query = Case.query.filter_by(office_id=office_id).filter(Case.status.in_(["active", "awaiting_judgment", "new"]))
    active_cases = active_cases_query.all()
    by_type = defaultdict(int)
    for case in active_cases:
        key = str(getattr(case.case_type, "value", case.case_type))
        by_type[key] += 1

    today_sessions_items = (
        HearingSession.query.filter_by(office_id=office_id)
        .filter(HearingSession.session_date == today)
        .order_by(HearingSession.session_time.asc())
        .all()
    )
    today_sessions = []
    for item in today_sessions_items:
        case = Case.query.filter_by(id=item.case_id, office_id=office_id).first()
        client = Client.query.filter_by(id=case.client_id, office_id=office_id, is_deleted=False).first() if case else None
        today_sessions.append(
            {
                "case": case.case_number if case else None,
                "client": client.full_name_ar if client else None,
                "court": item.court,
                "time": item.session_time.isoformat() if item.session_time else None,
                "lawyer": str(case.responsible_lawyer_id) if case else None,
            }
        )

    week_start = today - timedelta(days=today.weekday())
    week_sessions = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        count = HearingSession.query.filter_by(office_id=office_id).filter(HearingSession.session_date == d).count()
        week_sessions.append({"date": d.isoformat(), "count": count})

    overdue_tasks = Task.query.filter_by(office_id=office_id).filter(Task.deadline < datetime.utcnow(), Task.status != "done").count()
    expiring_poa = (
        PowerOfAttorney.query.filter_by(office_id=office_id)
        .filter(PowerOfAttorney.expiry_date.isnot(None), PowerOfAttorney.expiry_date <= today + timedelta(days=30))
        .count()
    )
    critical_appeal_deadlines = (
        AppealReminder.query.filter_by(office_id=office_id, sent=False)
        .filter(AppealReminder.days_before <= 7)
        .count()
    )

    month_start = date(today.year, today.month, 1)
    collected = (
        Payment.query.filter_by(office_id=office_id)
        .filter(Payment.payment_date >= month_start)
        .with_entities(func.coalesce(func.sum(Payment.amount), 0))
        .scalar()
    )
    outstanding = (
        Invoice.query.filter_by(office_id=office_id)
        .filter(Invoice.status != "paid")
        .with_entities(func.coalesce(func.sum(Invoice.total), 0))
        .scalar()
    )
    target = float(collected or 0) * 1.2 if collected else 10000.0
    collection_rate = (float(collected or 0) / target * 100) if target else 0

    ninety_days_ago = today - timedelta(days=90)
    recent_judgments = Judgment.query.filter_by(office_id=office_id).filter(Judgment.judgment_date >= ninety_days_ago).all()
    wins = sum(1 for item in recent_judgments if str(getattr(item.result, "value", item.result)) in {"full_win", "partial_win"})
    win_rate = round((wins / len(recent_judgments) * 100), 2) if recent_judgments else 0

    my_tasks_today = (
        Task.query.filter_by(office_id=office_id, assigned_to=g.current_user.id)
        .filter(Task.deadline.isnot(None))
        .filter(func.date(Task.deadline) == today)
        .order_by(Task.priority.asc(), Task.deadline.asc())
        .all()
    )

    return ok(
        data={
            "active_cases": {"total": len(active_cases), "by_type": dict(by_type)},
            "today_sessions": today_sessions,
            "week_sessions": week_sessions,
            "urgent_alerts": {
                "overdue_tasks": overdue_tasks,
                "expiring_poa": expiring_poa,
                "critical_appeal_deadlines": critical_appeal_deadlines,
            },
            "financial": {
                "collected_this_month": float(collected or 0),
                "outstanding": float(outstanding or 0),
                "target": round(target, 2),
                "collection_rate": round(collection_rate, 2),
            },
            "win_rate": {"last_90_days_percent": win_rate},
            "my_tasks_today": [
                {
                    "title": item.title,
                    "priority": str(getattr(item.priority, "value", item.priority)),
                    "deadline": item.deadline.isoformat() if item.deadline else None,
                }
                for item in my_tasks_today
            ],
        }
    )


@bp.get("/calendar-week")
@auth_required
def calendar_week():
    start = date.today()
    end = start + timedelta(days=6)

    sessions = (
        HearingSession.query.filter_by(office_id=g.current_user.office_id)
        .filter(HearingSession.session_date >= start, HearingSession.session_date <= end)
        .order_by(HearingSession.session_date.asc(), HearingSession.session_time.asc())
        .all()
    )
    return ok(data=[model_to_dict(item) for item in sessions])
