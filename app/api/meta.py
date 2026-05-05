from __future__ import annotations

import re
from datetime import datetime, timezone
from http import HTTPStatus

from flask import Blueprint, current_app, render_template_string

from app.services.meta_data import get_egyptian_courts, get_egyptian_governorates
from app.utils.responses import ok

bp = Blueprint("meta", __name__, url_prefix="/api/v1/meta")

_DYNAMIC_SEGMENT_PATTERN = re.compile(r"<(?:(?P<converter>[^:<>]+):)?(?P<name>[^<>]+)>")
_TESTER_PATH_PREFIX = "/api/v1/meta/endpoint-tester"

_ENDPOINT_TESTER_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>LexOffice Endpoint Tester</title>
    <style>
        :root {
            color-scheme: light;
            --bg: #f6f7fb;
            --panel: #ffffff;
            --line: #d6dae5;
            --text: #111827;
            --ok: #0f766e;
            --fail: #b91c1c;
            --button: #0f172a;
            --button-text: #ffffff;
        }
        body {
            margin: 0;
            font-family: "Segoe UI", Tahoma, sans-serif;
            background: linear-gradient(180deg, #eef2ff 0%, var(--bg) 100%);
            color: var(--text);
        }
        main {
            max-width: 1000px;
            margin: 48px auto;
            padding: 24px;
            border: 1px solid var(--line);
            border-radius: 14px;
            background: var(--panel);
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
        }
        h1 {
            margin: 0 0 10px;
            font-size: 1.5rem;
        }
        p {
            margin: 0 0 16px;
            color: #374151;
        }
        button {
            border: 0;
            border-radius: 10px;
            padding: 12px 16px;
            font-size: 0.95rem;
            font-weight: 700;
            background: var(--button);
            color: var(--button-text);
            cursor: pointer;
        }
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        #summary {
            margin-top: 14px;
            font-size: 0.95rem;
        }
        table {
            margin-top: 16px;
            width: 100%;
            border-collapse: collapse;
            font-size: 0.86rem;
            background: #fff;
        }
        th, td {
            text-align: left;
            border: 1px solid var(--line);
            padding: 8px;
            vertical-align: top;
            word-break: break-word;
        }
        .ok {
            color: var(--ok);
            font-weight: 700;
        }
        .fail {
            color: var(--fail);
            font-weight: 700;
        }
        @media (max-width: 720px) {
            main {
                margin: 18px;
            }
            table {
                font-size: 0.78rem;
            }
        }
    </style>
</head>
<body>
    <main>
        <h1>Endpoint Test Runner</h1>
        <p>Click once to automatically hit all registered Flask endpoints and list their statuses.</p>
        <button id="run-tests">Run All Endpoint Tests</button>
        <div id="summary"></div>
        <table id="results" hidden>
            <thead>
                <tr>
                    <th>Result</th>
                    <th>Method</th>
                    <th>Path</th>
                    <th>Status</th>
                    <th>Endpoint</th>
                    <th>Detail</th>
                </tr>
            </thead>
            <tbody></tbody>
        </table>
    </main>

    <script>
        const button = document.getElementById("run-tests");
        const summary = document.getElementById("summary");
        const table = document.getElementById("results");
        const tbody = table.querySelector("tbody");

        button.addEventListener("click", async () => {
            button.disabled = true;
            button.textContent = "Running tests...";
            summary.textContent = "Running endpoint checks...";
            tbody.innerHTML = "";
            table.hidden = true;

            try {
                const response = await fetch("/api/v1/meta/endpoint-tester/run", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"}
                });

                const payload = await response.json();
                const data = payload.data || {};
                const stats = data.summary || {total: 0, passed: 0, failed: 0};
                const results = data.results || [];

                summary.innerHTML =
                    "Total: " + stats.total +
                    " | Passed: <span class='ok'>" + stats.passed + "</span>" +
                    " | Failed: <span class='fail'>" + stats.failed + "</span>" +
                    " | Duration: " + (data.duration_ms || 0) + " ms";

                for (const item of results) {
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td class="${item.passed ? "ok" : "fail"}">${item.passed ? "PASS" : "FAIL"}</td>
                        <td>${item.method}</td>
                        <td>${item.tested_path}</td>
                        <td>${item.status_code}</td>
                        <td>${item.endpoint}</td>
                        <td>${item.summary || ""}</td>
                    `;
                    tbody.appendChild(row);
                }
                table.hidden = false;
            } catch (error) {
                summary.textContent = "Failed to execute endpoint tests: " + error;
            } finally {
                button.disabled = false;
                button.textContent = "Run All Endpoint Tests";
            }
        });
    </script>
</body>
</html>
"""


def _sample_value_for_segment(converter: str | None) -> str:
    normalized = (converter or "string").lower()
    if normalized == "uuid":
        return "00000000-0000-0000-0000-000000000001"
    if normalized == "int":
        return "1"
    if normalized == "float":
        return "1.0"
    if normalized == "path":
        return "sample/path"
    return "sample"


def _materialize_rule_path(rule_path: str) -> str:
    def _replace(match: re.Match) -> str:
        return _sample_value_for_segment(match.group("converter"))

    return _DYNAMIC_SEGMENT_PATTERN.sub(_replace, rule_path)


def _extract_response_summary(response) -> str | None:
    payload = response.get_json(silent=True)
    if isinstance(payload, dict):
        if isinstance(payload.get("error"), dict):
            return payload["error"].get("message")
        message = payload.get("message")
        if isinstance(message, str) and message:
            return message
    text = response.get_data(as_text=True).strip().replace("\n", " ")
    if not text:
        return None
    return text[:140]


_SMOKE_PASS_REASONS: dict[int, str] = {
    HTTPStatus.BAD_REQUEST: "Validation rejected test payload",
    HTTPStatus.UNAUTHORIZED: "Auth guard rejected anonymous request",
    HTTPStatus.FORBIDDEN: "Permission/CSRF guard rejected request",
    HTTPStatus.NOT_FOUND: "Route handled request but resource was not found",
    HTTPStatus.UNPROCESSABLE_ENTITY: "Validation rejected malformed payload",
}


def _evaluate_smoke_result(status_code: int) -> tuple[bool, str | None]:
    if HTTPStatus.OK <= status_code < HTTPStatus.MULTIPLE_CHOICES:
        return True, None
    if HTTPStatus.MULTIPLE_CHOICES <= status_code < HTTPStatus.BAD_REQUEST:
        return True, "Redirect response"
    if status_code in _SMOKE_PASS_REASONS:
        return True, _SMOKE_PASS_REASONS[status_code]
    return False, None


def _route_entries_for_testing() -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for rule in current_app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        if rule.rule.startswith(_TESTER_PATH_PREFIX):
            continue

        methods = sorted(method for method in rule.methods if method not in {"HEAD", "OPTIONS"})
        if not methods:
            continue

        entries.append(
            {
                "endpoint": rule.endpoint,
                "path_template": rule.rule,
                "tested_path": _materialize_rule_path(rule.rule),
                "methods": methods,
            }
        )
    return entries


@bp.get("/endpoint-tester")
def endpoint_tester_page():
    return render_template_string(_ENDPOINT_TESTER_HTML)


@bp.post("/endpoint-tester/run")
def run_endpoint_tester():
    started_at = datetime.now(timezone.utc)
    results: list[dict[str, object]] = []

    with current_app.test_client() as client:
        for route_entry in _route_entries_for_testing():
            for method in route_entry["methods"]:
                kwargs = {
                    "method": method,
                    "path": route_entry["tested_path"],
                }
                if method in {"POST", "PUT", "PATCH"}:
                    kwargs["json"] = {}

                try:
                    response = client.open(**kwargs)
                    status_code = response.status_code
                    response_summary = _extract_response_summary(response)
                    passed, smoke_reason = _evaluate_smoke_result(status_code)
                    summary = response_summary
                    if smoke_reason:
                        summary = (
                            f"{smoke_reason}: {response_summary}"
                            if response_summary
                            else smoke_reason
                        )
                    if not passed and not summary:
                        summary = f"Unexpected status code: {status_code}"
                    results.append(
                        {
                            "passed": passed,
                            "method": method,
                            "path_template": route_entry["path_template"],
                            "tested_path": route_entry["tested_path"],
                            "endpoint": route_entry["endpoint"],
                            "status_code": status_code,
                            "summary": summary,
                        }
                    )
                except Exception as exc:
                    results.append(
                        {
                            "passed": False,
                            "method": method,
                            "path_template": route_entry["path_template"],
                            "tested_path": route_entry["tested_path"],
                            "endpoint": route_entry["endpoint"],
                            "status_code": HTTPStatus.INTERNAL_SERVER_ERROR,
                            "summary": str(exc),
                        }
                    )

    completed_at = datetime.now(timezone.utc)
    passed_count = sum(1 for row in results if row["passed"])
    total_count = len(results)

    return ok(
        data={
            "generated_at": started_at.isoformat(),
            "duration_ms": int((completed_at - started_at).total_seconds() * 1000),
            "summary": {
                "total": total_count,
                "passed": passed_count,
                "failed": total_count - passed_count,
            },
            "results": results,
        }
    )


@bp.get("/courts")
def courts():
    response, status = ok(data={"courts": list(get_egyptian_courts())})
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response, status


@bp.get("/governorates")
def governorates():
    response, status = ok(data={"governorates": list(get_egyptian_governorates())})
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response, status
