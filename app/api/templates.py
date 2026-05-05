from __future__ import annotations

from flask import Blueprint, Response, g

from app.api.common import load_payload
from app.extensions import db
from app.models import Case, Client, LegalTemplate
from app.models.enums import UserRole
from app.schemas.core import TemplateGenerateSchema, TemplateSchema
from app.services.pdf_service import build_simple_pdf, render_template_content
from app.utils.decorators import auth_required, require_permission
from app.utils.responses import fail, ok
from app.utils.serialization import model_to_dict

bp = Blueprint("templates", __name__, url_prefix="/api/v1/templates")


def _can_manage_templates(role):
    value = role.value if hasattr(role, "value") else role
    return value in {"owner", "partner"}


@bp.get("/")
@require_permission("templates", "use")
def list_templates():
    templates = LegalTemplate.query.filter(
        (LegalTemplate.office_id == g.current_user.office_id) | (LegalTemplate.office_id.is_(None))
    ).all()
    return ok(data=[model_to_dict(item) for item in templates])


@bp.post("/")
@auth_required
def create_template():
    if not _can_manage_templates(g.current_user.role):
        return fail("FORBIDDEN", "Only owner/partner can create templates", status=403)

    payload = load_payload(TemplateSchema)
    template = LegalTemplate(office_id=g.current_user.office_id, **payload)
    db.session.add(template)
    db.session.commit()
    return ok(data=model_to_dict(template), status=201)


@bp.get("/<uuid:template_id>")
@require_permission("templates", "use")
def get_template(template_id):
    template = LegalTemplate.query.filter_by(id=template_id).filter(
        (LegalTemplate.office_id == g.current_user.office_id) | (LegalTemplate.office_id.is_(None))
    ).first()
    if not template:
        return fail("NOT_FOUND", "Template not found", status=404)
    return ok(data=model_to_dict(template))


@bp.put("/<uuid:template_id>")
@auth_required
def update_template(template_id):
    if not _can_manage_templates(g.current_user.role):
        return fail("FORBIDDEN", "Only owner/partner can update templates", status=403)

    template = LegalTemplate.query.filter_by(id=template_id, office_id=g.current_user.office_id).first()
    if not template:
        return fail("NOT_FOUND", "Custom template not found", status=404)

    payload = load_payload(TemplateSchema, partial=True)
    for key, value in payload.items():
        setattr(template, key, value)
    db.session.commit()
    return ok(data=model_to_dict(template), message="Template updated")


@bp.post("/<uuid:template_id>/generate")
@require_permission("templates", "use")
def generate_from_template(template_id):
    template = LegalTemplate.query.filter_by(id=template_id).filter(
        (LegalTemplate.office_id == g.current_user.office_id) | (LegalTemplate.office_id.is_(None))
    ).first()
    if not template:
        return fail("NOT_FOUND", "Template not found", status=404)

    payload = load_payload(TemplateGenerateSchema)

    client = Client.query.filter_by(
        id=payload["client_id"],
        office_id=g.current_user.office_id,
        is_deleted=False,
    ).first()
    if not client:
        return fail("NOT_FOUND", "Client not found", status=404)

    case = None
    if payload.get("case_id"):
        case = Case.query.filter_by(id=payload["case_id"], office_id=g.current_user.office_id).first()

    context = {
        "client_name": client.full_name_ar,
        "client_number": client.client_number,
        "lawyer_name": g.current_user.full_name,
        "date": str(g.current_user.created_at.date()) if g.current_user.created_at else "",
    }

    if case:
        context.update(
            {
                "case_number": case.case_number,
                "court": case.court,
                "case_subject": case.case_subject or "",
            }
        )

    context.update(payload.get("overrides") or {})
    rendered = render_template_content(template.content, context)
    try:
        pdf_bytes = build_simple_pdf(template.name, rendered.splitlines() or [rendered])
    except RuntimeError as exc:
        return fail("DEPENDENCY_MISSING", str(exc), status=503)

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=template_{template.id}.pdf"},
    )
