from __future__ import annotations

from datetime import datetime

from flask import Blueprint, g, request

from app.api.common import load_payload
from app.extensions import db
from app.models import Task
from app.schemas.core import TaskSchema, TaskStatusSchema
from app.utils.decorators import require_permission
from app.utils.responses import fail, ok
from app.utils.serialization import model_to_dict

bp = Blueprint("tasks", __name__, url_prefix="/api/v1/tasks")


@bp.get("/")
@require_permission("cases", "read")
def list_tasks():
    query = Task.query.filter_by(office_id=g.current_user.office_id)

    for key in ["assigned_to", "case_id", "status", "priority"]:
        value = request.args.get(key)
        if value:
            query = query.filter(getattr(Task, key) == value)

    if request.args.get("overdue_only") == "true":
        query = query.filter(Task.deadline.isnot(None), Task.deadline < datetime.utcnow(), Task.status != "done")

    items = query.order_by(Task.created_at.desc()).all()
    return ok(data=[model_to_dict(item) for item in items])


@bp.post("/")
@require_permission("tasks", "assign")
def create_task():
    payload = load_payload(TaskSchema)
    task = Task(office_id=g.current_user.office_id, assigned_by=g.current_user.id, **payload)
    db.session.add(task)
    db.session.commit()
    return ok(data=model_to_dict(task), status=201)


@bp.get("/<uuid:task_id>")
@require_permission("cases", "read")
def get_task(task_id):
    task = Task.query.filter_by(id=task_id, office_id=g.current_user.office_id).first()
    if not task:
        return fail("NOT_FOUND", "Task not found", status=404)
    return ok(data=model_to_dict(task))


@bp.put("/<uuid:task_id>")
@require_permission("tasks", "assign")
def update_task(task_id):
    task = Task.query.filter_by(id=task_id, office_id=g.current_user.office_id).first()
    if not task:
        return fail("NOT_FOUND", "Task not found", status=404)

    payload = load_payload(TaskSchema, partial=True)
    for key, value in payload.items():
        setattr(task, key, value)
    task.updated_at = datetime.utcnow()
    db.session.commit()
    return ok(data=model_to_dict(task), message="Task updated")


@bp.put("/<uuid:task_id>/status")
@require_permission("cases", "read")
def update_task_status(task_id):
    task = Task.query.filter_by(id=task_id, office_id=g.current_user.office_id).first()
    if not task:
        return fail("NOT_FOUND", "Task not found", status=404)

    payload = load_payload(TaskStatusSchema)
    task.status = payload["status"]
    task.updated_at = datetime.utcnow()
    db.session.commit()
    return ok(data=model_to_dict(task), message="Task status updated")


@bp.delete("/<uuid:task_id>")
@require_permission("tasks", "assign")
def delete_task(task_id):
    task = Task.query.filter_by(id=task_id, office_id=g.current_user.office_id).first()
    if not task:
        return fail("NOT_FOUND", "Task not found", status=404)

    db.session.delete(task)
    db.session.commit()
    return ok(data={}, message="Task deleted")


@bp.get("/my-tasks")
@require_permission("cases", "read")
def my_tasks():
    items = (
        Task.query.filter_by(office_id=g.current_user.office_id, assigned_to=g.current_user.id)
        .order_by(Task.priority.asc(), Task.deadline.asc())
        .all()
    )
    return ok(data=[model_to_dict(item) for item in items])


@bp.get("/board/<uuid:case_id>")
@require_permission("cases", "read")
def board(case_id):
    tasks = Task.query.filter_by(office_id=g.current_user.office_id, case_id=case_id).all()
    board_data = {
        "new": [model_to_dict(item) for item in tasks if str(getattr(item.status, "value", item.status)) == "new"],
        "in_progress": [
            model_to_dict(item) for item in tasks if str(getattr(item.status, "value", item.status)) == "in_progress"
        ],
        "done": [model_to_dict(item) for item in tasks if str(getattr(item.status, "value", item.status)) == "done"],
    }
    return ok(data=board_data)
