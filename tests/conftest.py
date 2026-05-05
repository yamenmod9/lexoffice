from __future__ import annotations

from datetime import datetime

import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import Office, User
from app.models.enums import UserRole
from app.utils.security import hash_password


class LocalTestConfig(TestConfig):
    SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"
    SECRET_KEY = "test-secret"
    JWT_SECRET_KEY = "test-jwt-secret"
    TESTING = True


@pytest.fixture()
def app():
    app = create_app(LocalTestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db_session(app):
    with app.app_context():
        yield db.session


@pytest.fixture()
def make_user(app, db_session):
    def _make_user(email: str, role: UserRole = UserRole.OWNER, office_name: str = "Office A"):
        office = Office(name=office_name, official_email=f"{office_name.lower().replace(' ', '')}@x.test")
        db_session.add(office)
        db_session.flush()

        user = User(
            office_id=office.id,
            full_name="Test User",
            email=email,
            phone="01000000000",
            password_hash=hash_password("P@ssword1"),
            role=role,
            notification_preferences={},
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db_session.add(user)
        db_session.commit()
        return office, user

    return _make_user


@pytest.fixture()
def token_for(app):
    def _token_for(user):
        with app.app_context():
            token = create_access_token(
                identity=str(user.id),
                additional_claims={"office_id": str(user.office_id), "role": user.role.value},
            )
        return token

    return _token_for


@pytest.fixture()
def auth_headers(token_for):
    def _auth_headers(user):
        token = token_for(user)
        return {"Authorization": f"Bearer {token}", "X-CSRF-Token": "test-csrf"}

    return _auth_headers
