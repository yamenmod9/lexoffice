from app.models.enums import UserRole


def test_accountant_cannot_create_client(client, make_user, auth_headers):
    _, accountant = make_user("acc@example.com", role=UserRole.ACCOUNTANT)

    response = client.post(
        "/api/v1/clients/",
        headers=auth_headers(accountant),
        json={
            "client_type": "individual",
            "full_name_ar": "عميل",
            "national_id_or_commercial_reg": "123",
            "primary_phone": "0100000",
        },
    )
    assert response.status_code == 403


def test_owner_can_create_client(client, make_user, auth_headers):
    _, owner = make_user("owner-rbac@example.com", role=UserRole.OWNER)

    response = client.post(
        "/api/v1/clients/",
        headers=auth_headers(owner),
        json={
            "client_type": "individual",
            "full_name_ar": "عميل",
            "national_id_or_commercial_reg": "123",
            "primary_phone": "0100000",
        },
    )
    assert response.status_code == 201


def test_reports_access_by_role(client, make_user, auth_headers):
    _, accountant = make_user("acc-reports@example.com", role=UserRole.ACCOUNTANT)
    _, junior = make_user("junior-reports@example.com", role=UserRole.JUNIOR_LAWYER)

    # Accountant can access financial-scoped reports.
    financial_report = client.get("/api/v1/reports/financial-monthly", headers=auth_headers(accountant))
    assert financial_report.status_code == 200

    # Accountant cannot access operational (non-financial) report endpoints.
    workload = client.get("/api/v1/reports/workload", headers=auth_headers(accountant))
    assert workload.status_code == 403

    # Junior lawyers are not allowed full reports.
    junior_report = client.get("/api/v1/reports/financial-monthly", headers=auth_headers(junior))
    assert junior_report.status_code == 403


def test_accountant_cannot_use_templates(client, make_user, auth_headers):
    _, accountant = make_user("acc-template@example.com", role=UserRole.ACCOUNTANT)

    response = client.get("/api/v1/templates/", headers=auth_headers(accountant))
    assert response.status_code == 403
