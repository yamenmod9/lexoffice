from __future__ import annotations

from datetime import datetime
from uuid import UUID

from flask import request


def get_pagination_params(default_per_page: int = 20, max_per_page: int = 100):
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", default_per_page)), 1), max_per_page)
    return page, per_page


def parse_datetime(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def parse_uuid(value):
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None
