from app.models.enums import UserRole


def _create_client(client, owner, auth_headers):
    response = client.post(
        "/api/v1/clients/",
        headers=auth_headers(owner),
        json={
            "client_type": "individual",
            "full_name_ar": "عميل تجريبي",
            "national_id_or_commercial_reg": "111",
            "primary_phone": "01000000000",
        },
    )
    assert response.status_code == 201
    return response.json["data"]


def _create_case(client, owner, auth_headers, client_id):
    response = client.post(
        "/api/v1/cases/",
        headers=auth_headers(owner),
        json={
            "case_number": "123",
            "case_year": 2026,
            "client_id": client_id,
            "court": "محكمة النقض",
            "case_type": "civil",
            "responsible_lawyer_id": owner.id,
            "client_role": "plaintiff",
            "fee_type": "fixed",
            "agreed_fee_amount": "1000",
        },
    )
    assert response.status_code == 201
    return response.json["data"]


def test_clients_cases_sessions_tasks_flow(client, make_user, auth_headers):
    _, owner = make_user("crud-owner@example.com", role=UserRole.OWNER)

    c = _create_client(client, owner, auth_headers)
    case = _create_case(client, owner, auth_headers, c["id"])

    session = client.post(
        "/api/v1/sessions/",
        headers=auth_headers(owner),
        json={
            "case_id": case["id"],
            "session_date": "2026-05-01",
            "session_type": "first",
        },
    )
    assert session.status_code == 201

    task = client.post(
        "/api/v1/tasks/",
        headers=auth_headers(owner),
        json={
            "title": "Prepare memo",
            "assigned_to": owner.id,
            "case_id": case["id"],
            "priority": "important",
            "status": "new",
        },
    )
    assert task.status_code == 201

    timeline = client.get(f"/api/v1/cases/{case['id']}/timeline", headers=auth_headers(owner))
    assert timeline.status_code == 200
    assert len(timeline.json["data"]) >= 1


def test_judgment_enforcement_poa_flow(client, make_user, auth_headers):
    _, owner = make_user("judge-owner@example.com", role=UserRole.OWNER)
    c = _create_client(client, owner, auth_headers)
    case = _create_case(client, owner, auth_headers, c["id"])

    judgment = client.post(
        "/api/v1/judgments/",
        headers=auth_headers(owner),
        json={
            "case_id": case["id"],
            "judgment_date": "2026-05-02",
            "judgment_type": "primary",
            "result": "full_win",
            "awarded_amount": "5000",
        },
    )
    assert judgment.status_code == 201
    judgment_id = judgment.json["data"]["id"]

    track = client.post(
        f"/api/v1/judgments/{judgment_id}/track-appeal",
        headers=auth_headers(owner),
        json={"appeal_type": "appeal", "appeal_deadline": "2026-06-01"},
    )
    assert track.status_code == 200

    open_enf = client.post(
        f"/api/v1/judgments/{judgment_id}/open-enforcement",
        headers=auth_headers(owner),
    )
    assert open_enf.status_code in {200, 201}

    poa = client.post(
        "/api/v1/poa/",
        headers=auth_headers(owner),
        json={
            "client_id": c["id"],
            "poa_type": "general",
            "issue_date": "2026-05-01",
            "responsible_lawyer_id": owner.id,
        },
    )
    assert poa.status_code == 201
