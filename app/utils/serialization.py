from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID


def _serialize_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(val) for key, val in value.items()}
    return value


def model_to_dict(model, exclude: set[str] | None = None):
    exclude = exclude or set()
    result = {}
    for column in model.__table__.columns:
        if column.name in exclude:
            continue
        result[column.name] = _serialize_value(getattr(model, column.name))
    return result
