from __future__ import annotations

from flask import Blueprint, g
from celery.result import AsyncResult

from app.api.common import load_payload
from app.models import Document
from app.schemas.core import AISummaryRequestSchema
from app.tasks.celery_app import get_celery
from app.tasks.jobs import summarize_document_task
from app.utils.decorators import auth_required
from app.utils.responses import fail, ok

bp = Blueprint("ai", __name__, url_prefix="/api/v1/ai")


@bp.post("/summarize")
@auth_required
def summarize():
    payload = load_payload(AISummaryRequestSchema)
    document = Document.query.filter_by(id=payload["document_id"], office_id=g.current_user.office_id).first()
    if not document:
        return fail("NOT_FOUND", "Document not found", status=404)

    task = summarize_document_task.delay(str(document.id))
    return ok(data={"task_id": task.id}, status=202)


@bp.get("/summary-status/<task_id>")
@auth_required
def summary_status(task_id):
    async_result = AsyncResult(task_id, app=get_celery())
    status = async_result.status.lower()

    if status == "success":
        result = async_result.result or {}
        return ok(data={"status": "ready", "summary": result.get("summary")})

    if status in {"failure", "revoked"}:
        return ok(data={"status": "failed", "summary": None})

    return ok(data={"status": "pending", "summary": None})
