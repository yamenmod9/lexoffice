from http import HTTPStatus

from flask import Flask
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from app.utils.responses import fail


def register_error_handlers(app: Flask):
    @app.errorhandler(ValidationError)
    def handle_validation_error(exc: ValidationError):
        return fail(
            "VALIDATION_ERROR",
            "Validation failed",
            fields=exc.messages,
            status=HTTPStatus.BAD_REQUEST,
        )

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(exc: IntegrityError):
        app.logger.exception("Integrity error: %s", exc)
        return fail(
            "INTEGRITY_ERROR",
            "A uniqueness or reference constraint failed",
            status=HTTPStatus.CONFLICT,
        )

    @app.errorhandler(HTTPException)
    def handle_http_error(exc: HTTPException):
        return fail(
            exc.name.upper().replace(" ", "_"),
            exc.description,
            status=exc.code,
        )

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        app.logger.exception("Unhandled error: %s", exc)
        return fail(
            "INTERNAL_SERVER_ERROR",
            "Unexpected server error",
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )
