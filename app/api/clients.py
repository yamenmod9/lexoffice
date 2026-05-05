from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from flask import Blueprint, Response, g, request
from sqlalchemy import func, or_

from app.api.common import load_payload, paginate_query
from app.extensions import db
from app.models import (
    AuditLog,
    Case,
    Client,
    ClientDocument,
    Invoice,
    Payment,
    PowerOfAttorney,
)
from app.schemas.core import ClientSchema
from app.services.pdf_service import build_simple_pdf
from app.services.storage_service import upload_file
from app.utils.decorators import require_permission
from app.utils.responses import fail, ok, paginated_meta
from app.utils.serialization import model_to_dict

bp = Blueprint("clients", __name__, url_prefix="/api/v1/clients")


@bp.get("/")
@require_permission("clients", "read")
def list_clients():
    query = Client.query.filter_by(office_id=g.current_user.office_id, is_deleted=False)

    q = request.args.get("q")
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Client.full_name_ar.ilike(like),
                Client.full_name_en.ilike(like),
                Client.national_id_or_commercial_reg.ilike(like),
            )
        )

    client_type = request.args.get("client_type")
    if client_type:
        query = query.filter(Client.client_type == client_type)

    assigned_lawyer_id = request.args.get("assigned_lawyer_id")
    if assigned_lawyer_id:
        query = query.filter(Client.assigned_lawyer_id == assigned_lawyer_id)

    sort_by = request.args.get("sort_by", "created_at")
    if hasattr(Client, sort_by):
        query = query.order_by(getattr(Client, sort_by).desc())
    else:
        query = query.order_by(Client.created_at.desc())

    pagination = paginate_query(query)
    return ok(
        data=[model_to_dict(item) for item in pagination.items],
        meta=paginated_meta(pagination),
    )


@bp.post("/")
@require_permission("clients", "create")
def create_client():
    payload = load_payload(ClientSchema)
    count = Client.query.filter_by(office_id=g.current_user.office_id).count()
    client_number = f"CL-{count + 1:06d}"

    client = Client(
        office_id=g.current_user.office_id,
        client_number=client_number,
        created_by=g.current_user.id,
        **payload,
    )
    db.session.add(client)
    db.session.commit()
    return ok(data=model_to_dict(client), status=201)


@bp.get("/<uuid:client_id>")
@require_permission("clients", "read")
def get_client(client_id):
    client = Client.query.filter_by(id=client_id, office_id=g.current_user.office_id, is_deleted=False).first()
    if not client:
        return fail("NOT_FOUND", "Client not found", status=404)
    return ok(data=model_to_dict(client))


@bp.put("/<uuid:client_id>")
@require_permission("clients", "update")
def update_client(client_id):
    client = Client.query.filter_by(id=client_id, office_id=g.current_user.office_id, is_deleted=False).first()
    if not client:
        return fail("NOT_FOUND", "Client not found", status=404)

    payload = load_payload(ClientSchema, partial=True)
    for key, value in payload.items():
        setattr(client, key, value)
    client.updated_at = datetime.utcnow()
    db.session.commit()
    return ok(data=model_to_dict(client), message="Client updated")


@bp.delete("/<uuid:client_id>")
@require_permission("clients", "update")
def delete_client(client_id):
    client = Client.query.filter_by(id=client_id, office_id=g.current_user.office_id, is_deleted=False).first()
    if not client:
        return fail("NOT_FOUND", "Client not found", status=404)

    client.is_deleted = True
    client.deleted_at = datetime.utcnow()
    db.session.commit()
    return ok(data={}, message="Client deleted")


@bp.get("/<uuid:client_id>/cases")
@require_permission("cases", "read")
def client_cases(client_id):
    cases = Case.query.filter_by(client_id=client_id, office_id=g.current_user.office_id).order_by(Case.created_at.desc()).all()
    return ok(data=[model_to_dict(item) for item in cases])


@bp.get("/<uuid:client_id>/financial")
@require_permission("financial", "report")
def client_financial(client_id):
    payments = Payment.query.filter_by(client_id=client_id, office_id=g.current_user.office_id).all()
    invoices = Invoice.query.filter_by(client_id=client_id, office_id=g.current_user.office_id).all()

    total_paid = float(sum(item.amount for item in payments) or 0)
    total_invoiced = float(sum(item.total for item in invoices) or 0)

    ledger = {
        "payments": [model_to_dict(item) for item in payments],
        "invoices": [model_to_dict(item) for item in invoices],
    }
    return ok(
        data={
            "total_paid": total_paid,
            "total_invoiced": total_invoiced,
            "outstanding": max(total_invoiced - total_paid, 0),
            "ledger": ledger,
        }
    )


@bp.get("/<uuid:client_id>/powers-of-attorney")
@require_permission("clients", "read")
def client_poa(client_id):
    poas = PowerOfAttorney.query.filter_by(client_id=client_id, office_id=g.current_user.office_id).all()
    return ok(data=[model_to_dict(item) for item in poas])


@bp.get("/<uuid:client_id>/documents")
@require_permission("clients", "read")
def client_documents(client_id):
    docs = ClientDocument.query.filter_by(client_id=client_id, office_id=g.current_user.office_id).all()
    return ok(data=[model_to_dict(item) for item in docs])


@bp.get("/<uuid:client_id>/activity-log")
@require_permission("clients", "read")
def client_activity_log(client_id):
    logs = (
        AuditLog.query.filter_by(office_id=g.current_user.office_id, entity_id=client_id)
        .order_by(AuditLog.created_at.desc())
        .all()
    )
    return ok(data=[model_to_dict(item) for item in logs])


@bp.post("/<uuid:client_id>/documents")
@require_permission("clients", "update")
def upload_client_document(client_id):
    client = Client.query.filter_by(id=client_id, office_id=g.current_user.office_id, is_deleted=False).first()
    if not client:
        return fail("NOT_FOUND", "Client not found", status=404)

    file = request.files.get("file")
    doc_type = request.form.get("doc_type", "other")
    if not file:
        return fail("VALIDATION_ERROR", "file is required", status=400)

    file_url, _ = upload_file(file, g.current_user.office_id, "client", client_id)
    doc = ClientDocument(
        client_id=client_id,
        office_id=g.current_user.office_id,
        doc_type=doc_type,
        file_url=file_url,
        file_name=file.filename,
        uploaded_by=g.current_user.id,
    )
    db.session.add(doc)
    db.session.commit()
    return ok(data=model_to_dict(doc), status=201)


@bp.delete("/<uuid:client_id>/documents/<uuid:doc_id>")
@require_permission("clients", "update")
def delete_client_document(client_id, doc_id):
    doc = ClientDocument.query.filter_by(
        id=doc_id,
        client_id=client_id,
        office_id=g.current_user.office_id,
    ).first()
    if not doc:
        return fail("NOT_FOUND", "Document not found", status=404)

    db.session.delete(doc)
    db.session.commit()
    return ok(data={}, message="Document deleted")


@bp.get("/<uuid:client_id>/statement")
@require_permission("financial", "report")
def generate_client_statement(client_id):
    client = Client.query.filter_by(id=client_id, office_id=g.current_user.office_id, is_deleted=False).first()
    if not client:
        return fail("NOT_FOUND", "Client not found", status=404)

    payments = Payment.query.filter_by(client_id=client_id, office_id=g.current_user.office_id).all()
    invoices = Invoice.query.filter_by(client_id=client_id, office_id=g.current_user.office_id).all()

    lines = [
        f"Client: {client.full_name_ar}",
        f"Client Number: {client.client_number}",
        "",
        "Invoices:",
    ]
    for invoice in invoices:
        lines.append(f"- {invoice.invoice_number} | total={invoice.total} | status={invoice.status}")

    lines.append("")
    lines.append("Payments:")
    for payment in payments:
        lines.append(f"- {payment.payment_date} | amount={payment.amount} | method={payment.payment_method}")

    pdf_bytes = build_simple_pdf("Client Statement", lines)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=client_statement_{client_id}.pdf"},
    )
