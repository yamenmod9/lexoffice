from app.api.meta import _evaluate_smoke_result


def test_courts_meta_endpoint_is_cached(client):
    response = client.get("/api/v1/meta/courts")

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "public, max-age=86400"

    courts = response.json["data"]["courts"]
    assert "محكمة النقض" in courts
    assert "محكمة الاستئناف القاهرة" in courts
    assert "محكمة الأسرة القاهرة" in courts
    assert len(courts) >= 120


def test_governorates_meta_endpoint_is_cached(client):
    response = client.get("/api/v1/meta/governorates")

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "public, max-age=86400"

    governorates = response.json["data"]["governorates"]
    assert "القاهرة" in governorates
    assert "الجيزة" in governorates
    assert len(governorates) == 27


def test_endpoint_tester_page_loads(client):
    response = client.get("/api/v1/meta/endpoint-tester")

    assert response.status_code == 200
    assert b"Endpoint Test Runner" in response.data
    assert b"Run All Endpoint Tests" in response.data


def test_endpoint_tester_run_returns_summary_and_results(client):
    response = client.post("/api/v1/meta/endpoint-tester/run")

    assert response.status_code == 200
    assert response.json["success"] is True

    data = response.json["data"]
    summary = data["summary"]
    results = data["results"]

    assert isinstance(results, list)
    assert summary["total"] == len(results)
    assert summary["passed"] + summary["failed"] == summary["total"]
    assert summary["total"] > 0

    for row in results:
        expected_passed, _ = _evaluate_smoke_result(row["status_code"])
        assert row["passed"] is expected_passed

    assert any(row["passed"] and row["status_code"] in {400, 401, 403, 404, 422} for row in results)

    tested_paths = {row["path_template"] for row in results}
    assert "/api/v1/meta/endpoint-tester" not in tested_paths
    assert "/api/v1/meta/endpoint-tester/run" not in tested_paths


def test_evaluate_smoke_result_classifies_expected_smoke_statuses():
    assert _evaluate_smoke_result(200)[0] is True
    assert _evaluate_smoke_result(302)[0] is True
    assert _evaluate_smoke_result(400)[0] is True
    assert _evaluate_smoke_result(401)[0] is True
    assert _evaluate_smoke_result(403)[0] is True
    assert _evaluate_smoke_result(404)[0] is True
    assert _evaluate_smoke_result(422)[0] is True
    assert _evaluate_smoke_result(500)[0] is False
