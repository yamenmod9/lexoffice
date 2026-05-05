from __future__ import annotations

import os
from pathlib import Path

from flask import Blueprint, g, request, send_file

from app.api.common import load_payload
from app.extensions import db
from app.models import Document
from app.schemas.core import DocumentUploadSchema
from app.services.storage_service import build_download_url, build_preview_url, delete_file, upload_file
from app.tasks.celery_app import celery_is_available
from app.tasks.jobs import summarize_document_task
from app.utils.decorators import require_permission
from app.utils.responses import fail, ok
from app.utils.serialization import model_to_dict

bp = Blueprint("documents", __name__, url_prefix="/api/v1/documents")


@bp.get("/")
@require_permission("cases", "read")
def list_documents():
    query = Document.query.filter_by(office_id=g.current_user.office_id)

    for key in ["entity_type", "entity_id", "doc_type"]:
        value = request.args.get(key)
        if value:
            query = query.filter(getattr(Document, key) == value)

    docs = query.order_by(Document.created_at.desc()).all()
    return ok(data=[model_to_dict(item) for item in docs])


@bp.post("/upload")
@require_permission("cases", "update")
def upload_document():
    file = request.files.get("file")
    if not file:
        return fail("VALIDATION_ERROR", "file is required", status=400)

    payload = DocumentUploadSchema().load(request.form.to_dict())

    file_url, key = upload_file(file, g.current_user.office_id, payload["entity_type"], payload["entity_id"])

    pos = file.stream.tell()
    file.stream.seek(0, os.SEEK_END)
    file_size = file.stream.tell()
    file.stream.seek(pos)

    doc = Document(
        office_id=g.current_user.office_id,
        entity_type=payload["entity_type"],
        entity_id=payload["entity_id"],
        doc_type=payload["doc_type"],
        file_name=payload.get("doc_name") or file.filename,
        file_url=file_url,
        file_size=file_size,
        mime_type=file.mimetype,
        uploaded_by=g.current_user.id,
    )
    db.session.add(doc)
    db.session.commit()
    return ok(data={**model_to_dict(doc), "key": key}, status=201)


@bp.get("/<uuid:document_id>")
@require_permission("cases", "read")
def document_metadata(document_id):
    doc = Document.query.filter_by(id=document_id, office_id=g.current_user.office_id).first()
    if not doc:
        return fail("NOT_FOUND", "Document not found", status=404)
    return ok(data=model_to_dict(doc))


@bp.get("/<uuid:document_id>/download")
@require_permission("cases", "read")
def download_document(document_id):
    doc = Document.query.filter_by(id=document_id, office_id=g.current_user.office_id).first()
    if not doc:
        return fail("NOT_FOUND", "Document not found", status=404)

    if doc.file_url.startswith("s3://"):
        key = "/".join(doc.file_url.split("/")[3:])
        return ok(data={"download_url": build_download_url(doc.file_url, key)})

    path = Path(doc.file_url)
    if not path.exists():
        return fail("NOT_FOUND", "File missing on storage", status=404)

    return send_file(path, as_attachment=True, download_name=doc.file_name)


@bp.get("/<uuid:document_id>/preview")
@require_permission("cases", "read")
def preview_document(document_id):
    doc = Document.query.filter_by(id=document_id, office_id=g.current_user.office_id).first()
    if not doc:
        return fail("NOT_FOUND", "Document not found", status=404)

    key = doc.file_url
    if doc.file_url.startswith("s3://"):
        key = "/".join(doc.file_url.split("/")[3:])
    return ok(data={"preview_url": build_preview_url(doc.file_url, key)})


@bp.delete("/<uuid:document_id>")
@require_permission("cases", "update")
def delete_document(document_id):
    doc = Document.query.filter_by(id=document_id, office_id=g.current_user.office_id).first()
    if not doc:
        return fail("NOT_FOUND", "Document not found", status=404)

    key = doc.file_url
    if doc.file_url.startswith("s3://"):
        key = "/".join(doc.file_url.split("/")[3:])
    delete_file(doc.file_url, key)

    db.session.delete(doc)
    db.session.commit()
    return ok(data={}, message="Document deleted")


@bp.post("/<uuid:document_id>/summarize")
@require_permission("cases", "read")
def summarize_document(document_id):
    if not celery_is_available():
        return fail("DEPENDENCY_MISSING", "Celery is not installed", status=503)

    doc = Document.query.filter_by(id=document_id, office_id=g.current_user.office_id).first()
    if not doc:
        return fail("NOT_FOUND", "Document not found", status=404)

    try:
        task = summarize_document_task.delay(str(document_id))
    except RuntimeError as exc:
        return fail("DEPENDENCY_MISSING", str(exc), status=503)
    return ok(data={"task_id": task.id}, status=202)


@bp.get("/<uuid:document_id>/summary")
@require_permission("cases", "read")
def get_document_summary(document_id):
    doc = Document.query.filter_by(id=document_id, office_id=g.current_user.office_id).first()
    if not doc:
        return fail("NOT_FOUND", "Document not found", status=404)

    return ok(
        data={
            "ready": bool(doc.ai_summary),
            "summary": doc.ai_summary,
            "requested_at": doc.ai_summary_requested_at.isoformat() if doc.ai_summary_requested_at else None,
        }
    )
