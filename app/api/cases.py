from __future__ import annotations

from datetime import datetime

from flask import Blueprint, g, request
from sqlalchemy import or_

from app.api.common import load_payload, paginate_query
from app.extensions import db
from app.models import (
    Case,
    CaseNote,
    Document,
    EnforcementFile,
    Expense,
    HearingSession,
    Judgment,
    Payment,
    Task,
)
from app.models.enums import EntityType
from app.schemas.core import CaseSchema, CaseStatusSchema, NotesSchema
from app.services.storage_service import upload_file
from app.utils.decorators import require_permission
from app.utils.responses import fail, ok, paginated_meta
from app.utils.serialization import model_to_dict

bp = Blueprint("cases", __name__, url_prefix="/api/v1/cases")


@bp.get("/")
@require_permission("cases", "read")
def list_cases():
    query = Case.query.filter_by(office_id=g.current_user.office_id)

    q = request.args.get("q")
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Case.case_number.ilike(like),
                Case.case_subject.ilike(like),
                Case.defendant_name.ilike(like),
            )
        )

    for key in ["status", "case_type", "priority", "responsible_lawyer_id", "client_id", "court"]:
        value = request.args.get(key)
        if value:
            query = query.filter(getattr(Case, key) == value)

    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    if date_from:
        query = query.filter(Case.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(Case.created_at <= datetime.fromisoformat(date_to))

    sort_by = request.args.get("sort_by", "created_at")
    if hasattr(Case, sort_by):
        query = query.order_by(getattr(Case, sort_by).desc())
    else:
        query = query.order_by(Case.created_at.desc())

    pagination = paginate_query(query)
    return ok(data=[model_to_dict(item) for item in pagination.items], meta=paginated_meta(pagination))


@bp.post("/")
@require_permission("cases", "create")
def create_case():
    payload = load_payload(CaseSchema)
    case = Case(office_id=g.current_user.office_id, created_by=g.current_user.id, **payload)
    db.session.add(case)
    db.session.commit()
    return ok(data=model_to_dict(case), status=201)


@bp.get("/<uuid:case_id>")
@require_permission("cases", "read")
def get_case(case_id):
    case = Case.query.filter_by(id=case_id, office_id=g.current_user.office_id).first()
    if not case:
        return fail("NOT_FOUND", "Case not found", status=404)
    return ok(data=model_to_dict(case))


@bp.put("/<uuid:case_id>")
@require_permission("cases", "update")
def update_case(case_id):
    case = Case.query.filter_by(id=case_id, office_id=g.current_user.office_id).first()
    if not case:
        return fail("NOT_FOUND", "Case not found", status=404)

    payload = load_payload(CaseSchema, partial=True)
    for key, value in payload.items():
        setattr(case, key, value)
    case.updated_at = datetime.utcnow()
    db.session.commit()
    return ok(data=model_to_dict(case), message="Case updated")


@bp.put("/<uuid:case_id>/status")
@require_permission("cases", "update")
def update_case_status(case_id):
    case = Case.query.filter_by(id=case_id, office_id=g.current_user.office_id).first()
    if not case:
        return fail("NOT_FOUND", "Case not found", status=404)

    payload = load_payload(CaseStatusSchema)
    case.status = payload["status"]
    case.updated_at = datetime.utcnow()
    db.session.commit()
    return ok(data=model_to_dict(case), message="Case status updated")


@bp.get("/<uuid:case_id>/sessions")
@require_permission("cases", "read")
def case_sessions(case_id):
    sessions = HearingSession.query.filter_by(case_id=case_id, office_id=g.current_user.office_id).all()
    return ok(data=[model_to_dict(item) for item in sessions])


@bp.get("/<uuid:case_id>/judgments")
@require_permission("cases", "read")
def case_judgments(case_id):
    judgments = Judgment.query.filter_by(case_id=case_id, office_id=g.current_user.office_id).all()
    return ok(data=[model_to_dict(item) for item in judgments])


@bp.get("/<uuid:case_id>/enforcement")
@require_permission("cases", "read")
def case_enforcement(case_id):
    enforcement = EnforcementFile.query.filter_by(case_id=case_id, office_id=g.current_user.office_id).first()
    return ok(data=model_to_dict(enforcement) if enforcement else None)


@bp.get("/<uuid:case_id>/tasks")
@require_permission("cases", "read")
def case_tasks(case_id):
    tasks = Task.query.filter_by(case_id=case_id, office_id=g.current_user.office_id).all()
    return ok(data=[model_to_dict(item) for item in tasks])


@bp.get("/<uuid:case_id>/documents")
@require_permission("cases", "read")
def case_documents(case_id):
    docs = Document.query.filter_by(
        office_id=g.current_user.office_id,
        entity_type=EntityType.CASE,
        entity_id=case_id,
    ).all()
    return ok(data=[model_to_dict(item) for item in docs])


@bp.post("/<uuid:case_id>/documents")
@require_permission("cases", "update")
def upload_case_document(case_id):
    file = request.files.get("file")
    doc_type = request.form.get("doc_type", "other")
    if not file:
        return fail("VALIDATION_ERROR", "file is required", status=400)

    file_url, _ = upload_file(file, g.current_user.office_id, "case", case_id)
    doc = Document(
        office_id=g.current_user.office_id,
        entity_type=EntityType.CASE,
        entity_id=case_id,
        doc_type=doc_type,
        file_name=file.filename,
        file_url=file_url,
        file_size=request.content_length or 0,
        mime_type=file.mimetype,
        uploaded_by=g.current_user.id,
    )
    db.session.add(doc)
    db.session.commit()
    return ok(data=model_to_dict(doc), status=201)


@bp.get("/<uuid:case_id>/financial")
@require_permission("financial", "report")
def case_financial(case_id):
    payments = Payment.query.filter_by(case_id=case_id, office_id=g.current_user.office_id).all()
    expenses = Expense.query.filter_by(case_id=case_id, office_id=g.current_user.office_id).all()

    fees_collected = float(sum(item.amount for item in payments) or 0)
    expenses_total = float(sum(item.amount for item in expenses) or 0)

    return ok(
        data={
            "fees_collected": fees_collected,
            "expenses_total": expenses_total,
            "net": fees_collected - expenses_total,
            "payments": [model_to_dict(item) for item in payments],
            "expenses": [model_to_dict(item) for item in expenses],
        }
    )


@bp.get("/<uuid:case_id>/timeline")
@require_permission("cases", "read")
def case_timeline(case_id):
    events = []

    case = Case.query.filter_by(id=case_id, office_id=g.current_user.office_id).first()
    if case:
        events.append({"type": "case_created", "at": case.created_at, "data": model_to_dict(case)})

    for session in HearingSession.query.filter_by(case_id=case_id, office_id=g.current_user.office_id).all():
        events.append({"type": "session", "at": session.created_at, "data": model_to_dict(session)})

    for judgment in Judgment.query.filter_by(case_id=case_id, office_id=g.current_user.office_id).all():
        events.append({"type": "judgment", "at": judgment.created_at, "data": model_to_dict(judgment)})

    for task in Task.query.filter_by(case_id=case_id, office_id=g.current_user.office_id).all():
        events.append({"type": "task", "at": task.created_at, "data": model_to_dict(task)})

    events.sort(key=lambda x: x["at"] or datetime.min, reverse=False)
    normalized = [{**item, "at": item["at"].isoformat() if item["at"] else None} for item in events]
    return ok(data=normalized)


@bp.get("/<uuid:case_id>/notes")
@require_permission("cases", "read")
def get_case_notes(case_id):
    notes = CaseNote.query.filter_by(case_id=case_id, office_id=g.current_user.office_id).order_by(CaseNote.created_at.desc()).all()
    return ok(data=[model_to_dict(item) for item in notes])


@bp.post("/<uuid:case_id>/notes")
@require_permission("cases", "update")
def add_case_note(case_id):
    payload = load_payload(NotesSchema)
    note = CaseNote(
        office_id=g.current_user.office_id,
        case_id=case_id,
        note=payload["note"],
        added_by=g.current_user.id,
    )
    db.session.add(note)
    db.session.commit()
    return ok(data=model_to_dict(note), status=201)
