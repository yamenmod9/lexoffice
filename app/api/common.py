from __future__ import annotations

from flask import abort, g, request
from marshmallow import ValidationError

from app.utils.helpers import get_pagination_params
from app.utils.responses import paginated_meta
from app.utils.serialization import model_to_dict


def load_payload(schema_cls, partial: bool = False):
    schema = schema_cls(partial=partial)
    body = request.get_json(silent=True) or {}
    return schema.load(body)


def to_json_list(items):
    return [model_to_dict(item) for item in items]


def paginate_query(query):
    page, per_page = get_pagination_params()
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return pagination


def object_or_404(query, object_id):
    instance = query.filter_by(id=object_id).first()
    if not instance:
        abort(404, description="Resource not found")
    return instance


def ensure_office(office_id):
    if office_id != g.current_user.office_id:
        abort(404, description="Resource not found")
