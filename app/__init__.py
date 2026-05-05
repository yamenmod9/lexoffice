from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, redirect, request, send_file

from app.api import register_blueprints
from app.config import Config
from app.extensions import cors, db, jwt, limiter, ma, mail, migrate
from app.tasks.celery_app import make_celery
from app.utils.audit_middleware import register_audit_middleware
from app.utils.errors import register_error_handlers


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    cors.init_app(app)
    limiter.init_app(app)

    with app.app_context():
        # Ensure models are imported before migrations/run.
        from app import models  # noqa: F401

    make_celery(app)

    register_blueprints(app)
    register_error_handlers(app)
    register_audit_middleware(app)

    @app.before_request
    def csrf_guard():
        if not app.config.get("ENFORCE_CSRF", True):
            return None
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "CSRF_TOKEN_MISSING",
                            "message": "X-CSRF-Token header is required",
                            "fields": {},
                        },
                    }
                ),
                403,
            )
        return None

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "lexoffice-backend"}

    @app.get("/endpoint-tester")
    def endpoint_tester():
        return redirect("/api/v1/meta/endpoint-tester")

    @app.get("/files/<path:key>")
    def local_file_proxy(key):
        root = Path(app.config["LOCAL_STORAGE_PATH"]).resolve()
        path = root / key
        if not path.exists() or not path.is_file():
            return {"error": "not_found"}, 404
        return send_file(path)

    return app
