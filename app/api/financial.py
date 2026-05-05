from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from flask import Blueprint, Response, g, request

from app.api.common import load_payload, paginate_query
from app.extensions import db
from app.models import Client, Expense, Invoice, Payment
from app.schemas.core import ExpenseSchema, InvoiceSchema, InvoiceStatusSchema, PaymentSchema
from app.services.notification_service import send_email_notification
from app.services.pdf_service import build_simple_pdf
from app.utils.decorators import require_permission
from app.utils.responses import fail, ok, paginated_meta
from app.utils.serialization import model_to_dict

bp = Blueprint("financial", __name__, url_prefix="/api/v1/financial")


def _calculate_invoice_totals(payload):
    subtotal = Decimal(str(payload["subtotal"]))
    discount_value = Decimal(str(payload.get("discount_value") or 0))
    discount_type = payload.get("discount_type")

    discounted = subtotal
    if discount_type == "percentage":
        discounted = subtotal - (subtotal * discount_value / Decimal("100"))
    elif discount_type == "fixed":
        discounted = subtotal - discount_value

    discounted = max(discounted, Decimal("0"))

    tax_enabled = payload.get("tax_enabled", True)
    tax_rate = Decimal(str(payload.get("tax_rate") or "0.14"))
    tax_amount = discounted * tax_rate if tax_enabled else Decimal("0")
    total = discounted + tax_amount
    return discounted, tax_amount, total


@bp.get("/payments")
@require_permission("financial", "report")
def list_payments():
    query = Payment.query.filter_by(office_id=g.current_user.office_id)

    for key in ["client_id", "case_id", "payment_method"]:
        value = request.args.get(key)
        if value:
            query = query.filter(getattr(Payment, key) == value)

    date_from = request.args.get("date_from")
    if date_from:
        query = query.filter(Payment.payment_date >= date.fromisoformat(date_from))

    date_to = request.args.get("date_to")
    if date_to:
        query = query.filter(Payment.payment_date <= date.fromisoformat(date_to))

    pagination = paginate_query(query.order_by(Payment.payment_date.desc()))
    return ok(data=[model_to_dict(item) for item in pagination.items], meta=paginated_meta(pagination))


@bp.post("/payments")
@require_permission("financial", "record")
def create_payment():
    payload = load_payload(PaymentSchema)
    payment = Payment(office_id=g.current_user.office_id, recorded_by=g.current_user.id, **payload)
    db.session.add(payment)
    db.session.commit()
    return ok(data=model_to_dict(payment), status=201)


@bp.get("/payments/<uuid:payment_id>")
@require_permission("financial", "report")
def get_payment(payment_id):
    payment = Payment.query.filter_by(id=payment_id, office_id=g.current_user.office_id).first()
    if not payment:
        return fail("NOT_FOUND", "Payment not found", status=404)
    return ok(data=model_to_dict(payment))


@bp.delete("/payments/<uuid:payment_id>")
@require_permission("financial", "record")
def delete_payment(payment_id):
    if g.current_user.role.value != "owner":
        return fail("FORBIDDEN", "Only owner can delete payment", status=403)

    payment = Payment.query.filter_by(id=payment_id, office_id=g.current_user.office_id).first()
    if not payment:
        return fail("NOT_FOUND", "Payment not found", status=404)

    db.session.delete(payment)
    db.session.commit()
    return ok(data={}, message="Payment deleted")


@bp.get("/invoices")
@require_permission("financial", "report")
def list_invoices():
    query = Invoice.query.filter_by(office_id=g.current_user.office_id)

    for key in ["status", "client_id"]:
        value = request.args.get(key)
        if value:
            query = query.filter(getattr(Invoice, key) == value)

    date_from = request.args.get("date_from")
    if date_from:
        query = query.filter(Invoice.issue_date >= date.fromisoformat(date_from))

    date_to = request.args.get("date_to")
    if date_to:
        query = query.filter(Invoice.issue_date <= date.fromisoformat(date_to))

    pagination = paginate_query(query.order_by(Invoice.issue_date.desc()))
    return ok(data=[model_to_dict(item) for item in pagination.items], meta=paginated_meta(pagination))


@bp.post("/invoices")
@require_permission("financial", "record")
def create_invoice():
    payload = load_payload(InvoiceSchema)

    count = Invoice.query.filter_by(office_id=g.current_user.office_id).count()
    invoice_number = f"INV-{count + 1:06d}"

    discounted, tax_amount, total = _calculate_invoice_totals(payload)
    invoice_data = dict(payload)
    invoice_data["subtotal"] = discounted
    invoice_data["tax_amount"] = tax_amount
    invoice_data["total"] = total

    invoice = Invoice(
        office_id=g.current_user.office_id,
        created_by=g.current_user.id,
        invoice_number=invoice_number,
        **invoice_data,
    )
    db.session.add(invoice)
    db.session.commit()
    return ok(data=model_to_dict(invoice), status=201)


@bp.get("/invoices/<uuid:invoice_id>")
@require_permission("financial", "report")
def get_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, office_id=g.current_user.office_id).first()
    if not invoice:
        return fail("NOT_FOUND", "Invoice not found", status=404)
    return ok(data=model_to_dict(invoice))


@bp.put("/invoices/<uuid:invoice_id>")
@require_permission("financial", "record")
def update_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, office_id=g.current_user.office_id).first()
    if not invoice:
        return fail("NOT_FOUND", "Invoice not found", status=404)

    if str(invoice.status) not in {"InvoiceStatus.DRAFT", "draft"} and getattr(invoice.status, "value", invoice.status) != "draft":
        return fail("INVALID_STATE", "Only draft invoices can be updated", status=400)

    payload = load_payload(InvoiceSchema, partial=True)
    merged = model_to_dict(invoice)
    merged.update(payload)
    discounted, tax_amount, total = _calculate_invoice_totals(merged)

    for key, value in payload.items():
        setattr(invoice, key, value)
    invoice.subtotal = discounted
    invoice.tax_amount = tax_amount
    invoice.total = total
    db.session.commit()
    return ok(data=model_to_dict(invoice), message="Invoice updated")


@bp.post("/invoices/<uuid:invoice_id>/send")
@require_permission("financial", "record")
def send_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, office_id=g.current_user.office_id).first()
    if not invoice:
        return fail("NOT_FOUND", "Invoice not found", status=404)

    client = Client.query.filter_by(id=invoice.client_id, office_id=g.current_user.office_id).first()
    if client and client.email:
        send_email_notification(
            client.email,
            f"Invoice {invoice.invoice_number}",
            f"Dear {client.full_name_ar}, your invoice amount is {invoice.total}",
        )

    invoice.status = "sent"
    db.session.commit()
    return ok(data=model_to_dict(invoice), message="Invoice sent")


@bp.get("/invoices/<uuid:invoice_id>/pdf")
@require_permission("financial", "report")
def invoice_pdf(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, office_id=g.current_user.office_id).first()
    if not invoice:
        return fail("NOT_FOUND", "Invoice not found", status=404)

    lines = [
        f"Invoice: {invoice.invoice_number}",
        f"Issue Date: {invoice.issue_date}",
        f"Due Date: {invoice.due_date}",
        f"Subtotal: {invoice.subtotal}",
        f"Tax: {invoice.tax_amount}",
        f"Total: {invoice.total}",
        f"Status: {invoice.status}",
        "",
        "Line items:",
    ]
    for item in invoice.line_items or []:
        lines.append(f"- {item.get('description')} | {item.get('amount')} | {item.get('type')}")

    pdf_bytes = build_simple_pdf("Invoice", lines)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice_{invoice.invoice_number}.pdf"},
    )


@bp.put("/invoices/<uuid:invoice_id>/status")
@require_permission("financial", "record")
def update_invoice_status(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, office_id=g.current_user.office_id).first()
    if not invoice:
        return fail("NOT_FOUND", "Invoice not found", status=404)

    payload = load_payload(InvoiceStatusSchema)
    invoice.status = payload["status"]
    db.session.commit()
    return ok(data=model_to_dict(invoice), message="Invoice status updated")


@bp.get("/expenses")
@require_permission("financial", "report")
def list_expenses():
    query = Expense.query.filter_by(office_id=g.current_user.office_id)

    for key in ["case_id", "expense_type"]:
        value = request.args.get(key)
        if value:
            query = query.filter(getattr(Expense, key) == value)

    date_from = request.args.get("date_from")
    if date_from:
        query = query.filter(Expense.expense_date >= date.fromisoformat(date_from))

    date_to = request.args.get("date_to")
    if date_to:
        query = query.filter(Expense.expense_date <= date.fromisoformat(date_to))

    items = query.order_by(Expense.expense_date.desc()).all()
    return ok(data=[model_to_dict(item) for item in items])


@bp.post("/expenses")
@require_permission("financial", "record")
def create_expense():
    payload = load_payload(ExpenseSchema)
    expense = Expense(office_id=g.current_user.office_id, recorded_by=g.current_user.id, **payload)
    db.session.add(expense)
    db.session.commit()
    return ok(data=model_to_dict(expense), status=201)


@bp.delete("/expenses/<uuid:expense_id>")
@require_permission("financial", "record")
def delete_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, office_id=g.current_user.office_id).first()
    if not expense:
        return fail("NOT_FOUND", "Expense not found", status=404)

    db.session.delete(expense)
    db.session.commit()
    return ok(data={}, message="Expense deleted")


@bp.get("/reports/monthly")
@require_permission("financial", "report")
def monthly_report():
    year = int(request.args.get("year", date.today().year))
    month = int(request.args.get("month", date.today().month))

    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    payments = (
        Payment.query.filter_by(office_id=g.current_user.office_id)
        .filter(Payment.payment_date >= start, Payment.payment_date < end)
        .all()
    )
    invoices = (
        Invoice.query.filter_by(office_id=g.current_user.office_id)
        .filter(Invoice.issue_date >= start, Invoice.issue_date < end)
        .all()
    )
    expenses = (
        Expense.query.filter_by(office_id=g.current_user.office_id)
        .filter(Expense.expense_date >= start, Expense.expense_date < end)
        .all()
    )

    total_collected = float(sum(item.amount for item in payments) or 0)
    total_invoiced = float(sum(item.total for item in invoices) or 0)
    total_expenses = float(sum(item.amount for item in expenses) or 0)

    return ok(
        data={
            "year": year,
            "month": month,
            "total_collected": total_collected,
            "total_invoiced": total_invoiced,
            "total_expenses": total_expenses,
            "net": total_collected - total_expenses,
        }
    )


@bp.get("/reports/client-statement/<uuid:client_id>")
@require_permission("financial", "report")
def client_statement(client_id):
    payments = Payment.query.filter_by(office_id=g.current_user.office_id, client_id=client_id).all()
    invoices = Invoice.query.filter_by(office_id=g.current_user.office_id, client_id=client_id).all()

    total_paid = float(sum(item.amount for item in payments) or 0)
    total_due = float(sum(item.total for item in invoices) or 0)

    return ok(
        data={
            "client_id": str(client_id),
            "total_paid": total_paid,
            "total_due": total_due,
            "outstanding": max(total_due - total_paid, 0),
            "payments": [model_to_dict(item) for item in payments],
            "invoices": [model_to_dict(item) for item in invoices],
        }
    )


@bp.get("/reports/overdue")
@require_permission("financial", "report")
def overdue_report():
    today = date.today()
    overdue = (
        Invoice.query.filter_by(office_id=g.current_user.office_id)
        .filter(Invoice.due_date.isnot(None), Invoice.due_date < today)
        .filter(Invoice.status != "paid")
        .all()
    )
    return ok(data=[model_to_dict(item) for item in overdue])


@bp.get("/reports/summary")
@require_permission("financial", "report")
def summary_report():
    today = date.today()
    month_start = date(today.year, today.month, 1)

    payments = (
        Payment.query.filter_by(office_id=g.current_user.office_id)
        .filter(Payment.payment_date >= month_start)
        .all()
    )
    invoices = Invoice.query.filter_by(office_id=g.current_user.office_id).all()

    total_collected_this_month = float(sum(item.amount for item in payments) or 0)
    total_outstanding = float(sum(item.total for item in invoices if str(getattr(item.status, 'value', item.status)) != "paid") or 0)
    total_invoiced = float(sum(item.total for item in invoices) or 0)
    collection_rate = (total_collected_this_month / total_invoiced * 100) if total_invoiced else 0.0

    return ok(
        data={
            "total_collected_this_month": total_collected_this_month,
            "total_outstanding": total_outstanding,
            "collection_rate": round(collection_rate, 2),
        }
    )
