from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint, g, request

from app.api.common import load_payload
from app.extensions import db
from app.models import AppealReminder, EnforcementFile, Judgment
from app.schemas.core import JudgmentSchema, TrackAppealSchema
from app.utils.decorators import require_permission
from app.utils.responses import fail, ok
from app.utils.serialization import model_to_dict

bp = Blueprint("judgments", __name__, url_prefix="/api/v1/judgments")


@bp.get("/")
@require_permission("cases", "read")
def list_judgments():
    query = Judgment.query.filter_by(office_id=g.current_user.office_id)

    case_id = request.args.get("case_id")
    if case_id:
        query = query.filter(Judgment.case_id == case_id)

    result = request.args.get("result")
    if result:
        query = query.filter(Judgment.result == result)

    items = query.order_by(Judgment.judgment_date.desc()).all()
    return ok(data=[model_to_dict(item) for item in items])


@bp.post("/")
@require_permission("cases", "update")
def create_judgment():
    payload = load_payload(JudgmentSchema)
    judgment = Judgment(office_id=g.current_user.office_id, added_by=g.current_user.id, **payload)
    db.session.add(judgment)
    db.session.commit()
    return ok(data=model_to_dict(judgment), status=201)


@bp.get("/<uuid:judgment_id>")
@require_permission("cases", "read")
def get_judgment(judgment_id):
    judgment = Judgment.query.filter_by(id=judgment_id, office_id=g.current_user.office_id).first()
    if not judgment:
        return fail("NOT_FOUND", "Judgment not found", status=404)
    return ok(data=model_to_dict(judgment))


@bp.put("/<uuid:judgment_id>")
@require_permission("cases", "update")
def update_judgment(judgment_id):
    judgment = Judgment.query.filter_by(id=judgment_id, office_id=g.current_user.office_id).first()
    if not judgment:
        return fail("NOT_FOUND", "Judgment not found", status=404)

    payload = load_payload(JudgmentSchema, partial=True)
    for key, value in payload.items():
        setattr(judgment, key, value)
    db.session.commit()
    return ok(data=model_to_dict(judgment), message="Judgment updated")


@bp.post("/<uuid:judgment_id>/track-appeal")
@require_permission("cases", "update")
def track_appeal(judgment_id):
    judgment = Judgment.query.filter_by(id=judgment_id, office_id=g.current_user.office_id).first()
    if not judgment:
        return fail("NOT_FOUND", "Judgment not found", status=404)

    payload = load_payload(TrackAppealSchema)
    judgment.appeal_tracked = True
    judgment.appeal_type = payload["appeal_type"]
    judgment.appeal_deadline = payload["appeal_deadline"]

    reminders = []
    for days_before in [30, 14, 7, 3]:
        remind_at = datetime.combine(payload["appeal_deadline"], datetime.min.time()) - timedelta(days=days_before)
        reminder = AppealReminder(
            judgment_id=judgment.id,
            office_id=g.current_user.office_id,
            remind_at=remind_at,
            days_before=days_before,
            sent=False,
        )
        db.session.add(reminder)
        reminders.append(reminder)

    db.session.commit()
    return ok(data={"judgment": model_to_dict(judgment), "reminders": [model_to_dict(r) for r in reminders]})


@bp.post("/<uuid:judgment_id>/open-enforcement")
@require_permission("cases", "update")
def open_enforcement(judgment_id):
    judgment = Judgment.query.filter_by(id=judgment_id, office_id=g.current_user.office_id).first()
    if not judgment:
        return fail("NOT_FOUND", "Judgment not found", status=404)

    existing = EnforcementFile.query.filter_by(judgment_id=judgment.id, office_id=g.current_user.office_id).first()
    if existing:
        return ok(data=model_to_dict(existing), message="Enforcement already exists")

    enforcement = EnforcementFile(
        case_id=judgment.case_id,
        judgment_id=judgment.id,
        office_id=g.current_user.office_id,
        official_enforcement_number=f"ENF-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        enforcement_court=judgment.court or "",
        enforcement_type="money_seizure",
        total_amount=judgment.awarded_amount or 0,
        debtor_name="",
        debtor_details={},
        start_date=datetime.utcnow().date(),
        status="active",
    )
    db.session.add(enforcement)
    db.session.commit()
    return ok(data=model_to_dict(enforcement), status=201)
