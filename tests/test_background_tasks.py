from datetime import datetime, timedelta

from app.extensions import db
from app.models import Client, Invoice, PowerOfAttorney, Task
from app.models.enums import PoaStatus, UserRole
from app.tasks.jobs import invoice_overdue_checker, poa_status_updater, task_overdue_checker


def test_poa_status_updater_task(make_user):
    office, owner = make_user("poa-task@example.com", role=UserRole.OWNER)

    client = Client(
        office_id=owner.office_id,
        client_number="CL-000001",
        client_type="individual",
        full_name_ar="عميل",
        national_id_or_commercial_reg="X1",
        primary_phone="0100",
    )
    db.session.add(client)
    db.session.flush()

    poa = PowerOfAttorney(
        office_id=owner.office_id,
        client_id=client.id,
        poa_type="general",
        issue_date=datetime.utcnow().date(),
        expiry_date=(datetime.utcnow() - timedelta(days=1)).date(),
        responsible_lawyer_id=owner.id,
        status=PoaStatus.ACTIVE,
    )
    db.session.add(poa)
    db.session.commit()

    result = poa_status_updater()
    assert result["updated"] >= 1


def test_task_overdue_checker_runs(make_user):
    office, owner = make_user("task-overdue@example.com", role=UserRole.OWNER)
    task = Task(
        office_id=owner.office_id,
        title="Old Task",
        assigned_to=owner.id,
        assigned_by=owner.id,
        priority="normal",
        status="new",
        deadline=datetime.utcnow() - timedelta(hours=2),
    )
    db.session.add(task)
    db.session.commit()

    result = task_overdue_checker()
    assert "sent" in result


def test_invoice_overdue_checker_runs(make_user):
    office, owner = make_user("invoice-overdue@example.com", role=UserRole.OWNER)

    client = Client(
        office_id=owner.office_id,
        client_number="CL-000001",
        client_type="individual",
        full_name_ar="عميل",
        national_id_or_commercial_reg="X2",
        primary_phone="0100",
    )
    db.session.add(client)
    db.session.flush()

    invoice = Invoice(
        office_id=owner.office_id,
        client_id=client.id,
        case_id=None,
        invoice_number="INV-000001",
        issue_date=datetime.utcnow().date(),
        due_date=(datetime.utcnow() - timedelta(days=2)).date(),
        line_items=[],
        subtotal=100,
        tax_amount=0,
        total=100,
        created_by=owner.id,
        status="sent",
    )
    db.session.add(invoice)
    db.session.commit()

    result = invoice_overdue_checker()
    assert "sent" in result
