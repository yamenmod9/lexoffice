from flask import jsonify


def ok(data=None, message=None, meta=None, status=200):
    payload = {
        "success": True,
        "data": data if data is not None else {},
        "meta": meta,
        "message": message,
    }
    return jsonify(payload), status


def fail(code, message, fields=None, status=400):
    payload = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "fields": fields or {},
        },
    }
    return jsonify(payload), status


def paginated_meta(pagination):
    return {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "total_pages": pagination.pages,
    }
