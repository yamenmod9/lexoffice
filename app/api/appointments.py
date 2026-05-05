from __future__ import annotations

from flask import Blueprint, g

from app.api.common import load_payload
from app.extensions import db
from app.models import Client, ClientAppointment
from app.schemas.core import AppointmentAttendanceSchema, AppointmentSchema
from app.services.notification_service import send_twilio_sms
from app.utils.decorators import require_permission
from app.utils.responses import fail, ok
from app.utils.serialization import model_to_dict

bp = Blueprint("appointments", __name__, url_prefix="/api/v1/appointments")


@bp.get("/")
@require_permission("clients", "read")
def list_appointments():
    items = (
        ClientAppointment.query.filter_by(office_id=g.current_user.office_id)
        .order_by(ClientAppointment.appointment_date.desc())
        .all()
    )
    return ok(data=[model_to_dict(item) for item in items])


@bp.post("/")
@require_permission("clients", "update")
def create_appointment():
    payload = load_payload(AppointmentSchema)
    appointment = ClientAppointment(office_id=g.current_user.office_id, **payload)
    db.session.add(appointment)

    client = Client.query.filter_by(id=payload["client_id"], office_id=g.current_user.office_id, is_deleted=False).first()
    if client:
        sms_body = f"Your appointment is scheduled for {payload['appointment_date']}"
        send_twilio_sms(client.primary_phone, sms_body)

    db.session.commit()
    return ok(data=model_to_dict(appointment), status=201)


@bp.get("/<uuid:appointment_id>")
@require_permission("clients", "read")
def get_appointment(appointment_id):
    item = ClientAppointment.query.filter_by(id=appointment_id, office_id=g.current_user.office_id).first()
    if not item:
        return fail("NOT_FOUND", "Appointment not found", status=404)
    return ok(data=model_to_dict(item))


@bp.put("/<uuid:appointment_id>")
@require_permission("clients", "update")
def update_appointment(appointment_id):
    item = ClientAppointment.query.filter_by(id=appointment_id, office_id=g.current_user.office_id).first()
    if not item:
        return fail("NOT_FOUND", "Appointment not found", status=404)

    payload = load_payload(AppointmentSchema, partial=True)
    for key, value in payload.items():
        setattr(item, key, value)

    db.session.commit()
    return ok(data=model_to_dict(item), message="Appointment updated")


@bp.post("/<uuid:appointment_id>/attendance")
@require_permission("clients", "update")
def record_attendance(appointment_id):
    item = ClientAppointment.query.filter_by(id=appointment_id, office_id=g.current_user.office_id).first()
    if not item:
        return fail("NOT_FOUND", "Appointment not found", status=404)

    payload = load_payload(AppointmentAttendanceSchema)
    item.attendance_status = payload["attendance_status"]
    db.session.commit()
    return ok(data=model_to_dict(item), message="Attendance recorded")
