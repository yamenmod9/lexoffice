from app.services.auth_service import build_register_token_key
from app.services.cache import get_json
from app.models import User


def test_register_verify_login_flow(client):
    register = client.post(
        "/api/v1/auth/register",
        json={
            "office_name": "Lex A",
            "full_name": "Owner A",
            "email": "owner@example.com",
            "phone": "01011111111",
            "password": "Secure@123",
        },
    )
    assert register.status_code == 201

    cached = get_json(build_register_token_key("owner@example.com"))
    assert cached
    otp = cached["otp"]

    verify = client.post("/api/v1/auth/verify-otp", json={"email": "owner@example.com", "otp": otp})
    assert verify.status_code == 200
    assert verify.json["success"] is True

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "Secure@123"},
    )
    assert login.status_code == 200
    assert "access_token" in login.json["data"]
    assert "refresh_token" in login.json["data"]


def test_forgot_reset_password_flow(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "office_name": "Lex B",
            "full_name": "Owner B",
            "email": "ownerb@example.com",
            "phone": "01022222222",
            "password": "Secure@123",
        },
    )
    otp = get_json(build_register_token_key("ownerb@example.com"))["otp"]
    client.post("/api/v1/auth/verify-otp", json={"email": "ownerb@example.com", "otp": otp})

    forgot = client.post("/api/v1/auth/forgot-password", json={"email": "ownerb@example.com"})
    assert forgot.status_code == 200

    from app.services.auth_service import build_reset_token_key

    reset_otp = get_json(build_reset_token_key("ownerb@example.com"))["otp"]
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"email": "ownerb@example.com", "otp": reset_otp, "new_password": "Newpass@123"},
    )
    assert reset.status_code == 200

    login = client.post("/api/v1/auth/login", json={"email": "ownerb@example.com", "password": "Newpass@123"})
    assert login.status_code == 200


def test_mfa_enable_verify_disable(app, client, db_session, make_user, auth_headers):
    _, user = make_user("mfa@example.com")

    enable = client.post("/api/v1/auth/mfa/enable", headers=auth_headers(user))
    assert enable.status_code == 200
    secret = enable.json["data"]["secret"]

    import pyotp

    code = pyotp.TOTP(secret).now()
    verify = client.post("/api/v1/auth/mfa/verify", headers=auth_headers(user), json={"code": code})
    assert verify.status_code == 200

    user = User.query.filter_by(id=user.id).first()
    assert user.mfa_enabled is True

    disable = client.post("/api/v1/auth/mfa/disable", headers=auth_headers(user), json={"password": "P@ssword1"})
    assert disable.status_code == 200
