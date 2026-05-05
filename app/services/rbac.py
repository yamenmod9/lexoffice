from __future__ import annotations

from dataclasses import dataclass

PERMISSIONS = {
    "owner": {
        "clients.create": "all",
        "clients.read": "all",
        "clients.update": "all",
        "cases.create": "all",
        "cases.read": "all",
        "cases.update": "all",
        "sessions.create": "all",
        "financial.record": "all",
        "financial.report": "all",
        "tasks.assign": "all",
        "members.manage": "all",
        "templates.use": "all",
        "reports.full": "all",
    },
    "partner": {
        "clients.create": "all",
        "clients.read": "all",
        "clients.update": "all",
        "cases.create": "all",
        "cases.read": "all",
        "cases.update": "all",
        "sessions.create": "all",
        "financial.record": "all",
        "financial.report": "all",
        "tasks.assign": "all",
        "templates.use": "all",
        "reports.full": "all",
    },
    "senior_lawyer": {
        "clients.create": "all",
        "clients.read": "team",
        "clients.update": "all",
        "cases.create": "all",
        "cases.read": "team",
        "cases.update": "team",
        "sessions.create": "all",
        "financial.record": "own",
        "financial.report": "own",
        "tasks.assign": "team",
        "templates.use": "all",
    },
    "junior_lawyer": {
        "clients.read": "own",
        "cases.read": "own",
        "cases.update": "own",
        "sessions.create": "all",
        "tasks.assign": "own",
        "templates.use": "all",
    },
    "assistant": {
        "clients.create": "all",
        "clients.read": "all",
        "clients.update": "all",
        "cases.read": "all",
        "sessions.create": "all",
        "templates.use": "print_only",
    },
    "accountant": {
        "financial.record": "all",
        "financial.report": "all",
        "reports.full": "financial",
    },
}


@dataclass
class PermissionDecision:
    allowed: bool
    scope: str | None = None


def get_permission_scope(role: str, permission_key: str) -> str | None:
    return PERMISSIONS.get(role, {}).get(permission_key)


def has_permission(role: str, permission_key: str) -> PermissionDecision:
    scope = get_permission_scope(role, permission_key)
    return PermissionDecision(allowed=scope is not None, scope=scope)
