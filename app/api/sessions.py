from __future__ import annotations

from datetime import date, datetime, timedelta

from flask import Blueprint, g, request

from app.api.common import load_payload, paginate_query
from app.extensions import db
from app.models import Case, HearingSession
from app.schemas.core import SessionResultSchema, SessionSchema
from app.services.storage_service import upload_file
from app.utils.decorators import require_permission
from app.utils.responses import fail, ok, paginated_meta
from app.utils.serialization import model_to_dict

bp = Blueprint("sessions", __name__, url_prefix="/api/v1/sessions")


@bp.get("/")
@require_permission("cases", "read")
def list_sessions():
    query = HearingSession.query.filter_by(office_id=g.current_user.office_id)

    date_from = request.args.get("date_from")
    if date_from:
        query = query.filter(HearingSession.session_date >= date.fromisoformat(date_from))

    date_to = request.args.get("date_to")
    if date_to:
        query = query.filter(HearingSession.session_date <= date.fromisoformat(date_to))

    case_id = request.args.get("case_id")
    if case_id:
        query = query.filter(HearingSession.case_id == case_id)

    court = request.args.get("court")
    if court:
        query = query.filter(HearingSession.court == court)

    result = request.args.get("result")
    if result:
        query = query.filter(HearingSession.result == result)

    lawyer_id = request.args.get("lawyer_id")
    if lawyer_id:
        query = query.join(Case, Case.id == HearingSession.case_id).filter(Case.responsible_lawyer_id == lawyer_id)

    query = query.order_by(HearingSession.session_date.asc())
    pagination = paginate_query(query)
    return ok(data=[model_to_dict(item) for item in pagination.items], meta=paginated_meta(pagination))


@bp.post("/")
@require_permission("sessions", "create")
def create_session():
    payload = load_payload(SessionSchema)
    case = Case.query.filter_by(id=payload["case_id"], office_id=g.current_user.office_id).first()
    if not case:
        return fail("NOT_FOUND", "Case not found", status=404)

    session_data = dict(payload)
    session_data["court"] = session_data.get("court") or case.court
    session_data["court_circuit"] = session_data.get("court_circuit") or case.court_circuit

    session_obj = HearingSession(
        office_id=g.current_user.office_id,
        added_by=g.current_user.id,
        **session_data,
    )
    db.session.add(session_obj)
    db.session.commit()
    return ok(data=model_to_dict(session_obj), status=201)


@bp.get("/calendar")
@require_permission("cases", "read")
def calendar_view():
    selected_date = request.args.get("date")
    anchor = date.fromisoformat(selected_date) if selected_date else date.today()
    view = request.args.get("view", "week")

    if view == "day":
        start = anchor
        end = anchor
    elif view == "month":
        start = anchor.replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    else:
        start = anchor - timedelta(days=anchor.weekday())
        end = start + timedelta(days=6)

    query = HearingSession.query.filter_by(office_id=g.current_user.office_id).filter(
        HearingSession.session_date >= start,
        HearingSession.session_date <= end,
    )

    lawyer_id = request.args.get("lawyer_id")
    if lawyer_id:
        query = query.join(Case, Case.id == HearingSession.case_id).filter(Case.responsible_lawyer_id == lawyer_id)

    sessions = query.order_by(HearingSession.session_date.asc()).all()
    return ok(data=[model_to_dict(item) for item in sessions])


@bp.get("/today")
@require_permission("cases", "read")
def today_sessions():
    query = (
        HearingSession.query.join(Case, Case.id == HearingSession.case_id)
        .filter(HearingSession.office_id == g.current_user.office_id)
        .filter(HearingSession.session_date == date.today())
    )

    if g.current_user.role.value in {"junior_lawyer", "senior_lawyer"}:
        query = query.filter(Case.responsible_lawyer_id == g.current_user.id)

    sessions = query.order_by(HearingSession.session_time.asc()).all()
    return ok(data=[model_to_dict(item) for item in sessions])


@bp.get("/upcoming")
@require_permission("cases", "read")
def upcoming_sessions():
    now = date.today()
    end = now + timedelta(days=7)
    sessions = (
        HearingSession.query.filter_by(office_id=g.current_user.office_id)
        .filter(HearingSession.session_date >= now, HearingSession.session_date <= end)
        .order_by(HearingSession.session_date.asc())
        .all()
    )
    return ok(data=[model_to_dict(item) for item in sessions])


@bp.get("/<uuid:session_id>")
@require_permission("cases", "read")
def get_session(session_id):
    session_obj = HearingSession.query.filter_by(id=session_id, office_id=g.current_user.office_id).first()
    if not session_obj:
        return fail("NOT_FOUND", "Session not found", status=404)
    return ok(data=model_to_dict(session_obj))


@bp.put("/<uuid:session_id>")
@require_permission("sessions", "create")
def update_session(session_id):
    session_obj = HearingSession.query.filter_by(id=session_id, office_id=g.current_user.office_id).first()
    if not session_obj:
        return fail("NOT_FOUND", "Session not found", status=404)

    payload = load_payload(SessionSchema, partial=True)
    for key, value in payload.items():
        setattr(session_obj, key, value)
    db.session.commit()
    return ok(data=model_to_dict(session_obj), message="Session updated")


@bp.post("/<uuid:session_id>/result")
@require_permission("sessions", "create")
def record_result(session_id):
    session_obj = HearingSession.query.filter_by(id=session_id, office_id=g.current_user.office_id).first()
    if not session_obj:
        return fail("NOT_FOUND", "Session not found", status=404)

    payload = load_payload(SessionResultSchema)
    session_obj.result = payload["result"]
    session_obj.result_notes = payload.get("result_notes")
    session_obj.next_session_date = payload.get("next_session_date")

    created_next = None
    if payload["result"] == "postponed" and payload.get("next_session_date"):
        created_next = HearingSession(
            case_id=session_obj.case_id,
            office_id=session_obj.office_id,
            session_date=payload["next_session_date"],
            session_time=session_obj.session_time,
            court=session_obj.court,
            court_circuit=session_obj.court_circuit,
            session_type="postponement",
            added_by=g.current_user.id,
        )
        db.session.add(created_next)

    db.session.commit()
    data = {
        "session": model_to_dict(session_obj),
        "next_session": model_to_dict(created_next) if created_next else None,
    }
    return ok(data=data, message="Session result recorded")


@bp.post("/<uuid:session_id>/minutes")
@require_permission("sessions", "create")
def upload_minutes(session_id):
    session_obj = HearingSession.query.filter_by(id=session_id, office_id=g.current_user.office_id).first()
    if not session_obj:
        return fail("NOT_FOUND", "Session not found", status=404)

    file = request.files.get("file")
    if not file:
        return fail("VALIDATION_ERROR", "file is required", status=400)

    file_url, _ = upload_file(file, g.current_user.office_id, "session", session_id)
    session_obj.minutes_file_url = file_url
    db.session.commit()
    return ok(data={"minutes_file_url": file_url})
