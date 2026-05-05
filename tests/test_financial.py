from app.models.enums import UserRole


def _create_client_case(client, owner, auth_headers):
    c = client.post(
        "/api/v1/clients/",
        headers=auth_headers(owner),
        json={
            "client_type": "individual",
            "full_name_ar": "عميل مالي",
            "national_id_or_commercial_reg": "222",
            "primary_phone": "01000000000",
        },
    ).json["data"]

    case = client.post(
        "/api/v1/cases/",
        headers=auth_headers(owner),
        json={
            "case_number": "C-999",
            "case_year": 2026,
            "client_id": c["id"],
            "court": "محكمة النقض",
            "case_type": "civil",
            "responsible_lawyer_id": owner.id,
            "client_role": "plaintiff",
            "fee_type": "fixed",
            "agreed_fee_amount": "1000",
        },
    ).json["data"]

    return c, case


def test_invoice_calculation_and_reports(client, make_user, auth_headers):
    _, owner = make_user("finance-owner@example.com", role=UserRole.OWNER)
    c, case = _create_client_case(client, owner, auth_headers)

    invoice = client.post(
        "/api/v1/financial/invoices",
        headers=auth_headers(owner),
        json={
            "client_id": c["id"],
            "case_id": case["id"],
            "issue_date": "2026-05-01",
            "line_items": [{"description": "Fee", "amount": 1000, "type": "fee"}],
            "subtotal": "1000",
            "discount_type": "percentage",
            "discount_value": "10",
            "tax_enabled": True,
            "tax_rate": "0.14",
        },
    )
    assert invoice.status_code == 201
    total = float(invoice.json["data"]["total"])
    assert total > 900

    payment = client.post(
        "/api/v1/financial/payments",
        headers=auth_headers(owner),
        json={
            "client_id": c["id"],
            "case_id": case["id"],
            "amount": "500",
            "payment_date": "2026-05-02",
            "payment_method": "cash",
        },
    )
    assert payment.status_code == 201

    summary = client.get("/api/v1/financial/reports/summary", headers=auth_headers(owner))
    assert summary.status_code == 200
    assert "collection_rate" in summary.json["data"]
