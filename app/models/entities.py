from __future__ import annotations

import uuid
from datetime import datetime, time

from sqlalchemy import Uuid
from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db
from app.models.enums import (
    AppealType,
    AttendanceStatus,
    CaseStatus,
    CaseType,
    ClientDocumentType,
    ClientRoleInCase,
    ClientType,
    DiscountType,
    EnforcementStatus,
    EnforcementType,
    EntityType,
    ExpenseType,
    FeeType,
    GlobalDocumentType,
    InvoiceStatus,
    JudgmentResult,
    JudgmentType,
    PaymentMethod,
    PoaStatus,
    PoaType,
    Priority,
    RecurrenceType,
    SessionResult,
    SessionType,
    SubscriptionPlan,
    SubscriptionStatus,
    TaskPriority,
    TaskStatus,
    TemplateType,
    UserRole,
)

JSON_TYPE = db.JSON().with_variant(JSONB, "postgresql")
ARRAY_STRING_TYPE = db.ARRAY(db.String()).with_variant(db.JSON(), "sqlite")


def enum_value_type(enum_cls, name: str):
    return db.Enum(
        enum_cls,
        name=name,
        values_callable=lambda enum: [member.value for member in enum],
        native_enum=False,
        validate_strings=True,
    )


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Office(db.Model, TimestampMixin):
    __tablename__ = "offices"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(255), nullable=False)
    logo_url = db.Column(db.String(1024), nullable=True)
    address = db.Column(db.Text, nullable=True)
    bar_association_number = db.Column(db.String(120), unique=True, nullable=True)
    primary_courts = db.Column(ARRAY_STRING_TYPE, nullable=True)
    official_phone = db.Column(db.String(40), nullable=True)
    fax = db.Column(db.String(40), nullable=True)
    official_email = db.Column(db.String(255), nullable=True)
    subscription_plan = db.Column(
        enum_value_type(SubscriptionPlan, "subscription_plan_enum"),
        default=SubscriptionPlan.STARTER,
        nullable=False,
    )
    subscription_status = db.Column(
        enum_value_type(SubscriptionStatus, "subscription_status_enum"),
        default=SubscriptionStatus.TRIAL,
        nullable=False,
    )
    trial_ends_at = db.Column(db.DateTime, nullable=True)

    users = db.relationship("User", back_populates="office", lazy="dynamic")


class User(db.Model, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    full_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    phone = db.Column(db.String(40), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(enum_value_type(UserRole, "user_role_enum"), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    mfa_enabled = db.Column(db.Boolean, default=False, nullable=False)
    mfa_secret = db.Column(db.String(255), nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    profile_picture_url = db.Column(db.String(1024), nullable=True)
    notification_preferences = db.Column(JSON_TYPE, default=dict, nullable=False)
    quiet_hours_start = db.Column(db.Time, default=time(22, 0), nullable=False)
    quiet_hours_end = db.Column(db.Time, default=time(8, 0), nullable=False)
    daily_digest_enabled = db.Column(db.Boolean, default=False, nullable=False)
    fcm_token = db.Column(db.String(1024), nullable=True)

    office = db.relationship("Office", back_populates="users")


class ActiveSession(db.Model, TimestampMixin):
    __tablename__ = "active_sessions"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False, index=True)
    device_name = db.Column(db.String(120), nullable=True)
    device_type = db.Column(db.String(80), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    refresh_token_hash = db.Column(db.String(255), nullable=False)
    last_active_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)

    user = db.relationship("User", lazy="joined")


class Client(db.Model, TimestampMixin):
    __tablename__ = "clients"
    __table_args__ = (db.UniqueConstraint("office_id", "client_number", name="uq_client_number_per_office"),)

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    client_number = db.Column(db.String(40), nullable=False)
    client_type = db.Column(enum_value_type(ClientType, "client_type_enum"), nullable=False)
    full_name_ar = db.Column(db.String(255), nullable=False)
    full_name_en = db.Column(db.String(255), nullable=True)
    national_id_or_commercial_reg = db.Column(db.String(100), nullable=False)
    date_of_birth_or_founding = db.Column(db.Date, nullable=True)
    nationality = db.Column(db.String(120), nullable=True)
    profession_or_activity = db.Column(db.String(255), nullable=True)
    governorate = db.Column(db.String(120), nullable=True)
    city = db.Column(db.String(120), nullable=True)
    district = db.Column(db.String(120), nullable=True)
    street = db.Column(db.String(255), nullable=True)
    building_number = db.Column(db.String(50), nullable=True)
    primary_phone = db.Column(db.String(40), nullable=False)
    secondary_phone = db.Column(db.String(40), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    whatsapp = db.Column(db.String(40), nullable=True)
    emergency_contact_name = db.Column(db.String(255), nullable=True)
    emergency_contact_phone = db.Column(db.String(40), nullable=True)
    emergency_contact_relation = db.Column(db.String(120), nullable=True)
    internal_notes = db.Column(db.Text, nullable=True)
    assigned_lawyer_id = db.Column(Uuid, db.ForeignKey("users.id"), nullable=True)
    created_by = db.Column(Uuid, db.ForeignKey("users.id"), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)


class ClientDocument(db.Model):
    __tablename__ = "client_documents"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id = db.Column(Uuid, db.ForeignKey("clients.id"), nullable=False, index=True)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    doc_type = db.Column(enum_value_type(ClientDocumentType, "client_doc_type_enum"), nullable=False)
    file_url = db.Column(db.String(1024), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Case(db.Model, TimestampMixin):
    __tablename__ = "cases"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    case_number = db.Column(db.String(120), nullable=False)
    case_year = db.Column(db.Integer, nullable=True)
    client_id = db.Column(Uuid, db.ForeignKey("clients.id"), nullable=False, index=True)
    court = db.Column(db.String(255), nullable=False)
    court_circuit = db.Column(db.String(255), nullable=True)
    case_type = db.Column(enum_value_type(CaseType, "case_type_enum"), nullable=False)
    case_subject = db.Column(db.Text, nullable=True)
    defendant_name = db.Column(db.String(255), nullable=True)
    defendant_lawyer = db.Column(db.String(255), nullable=True)
    responsible_lawyer_id = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False)
    assistant_lawyer_id = db.Column(Uuid, db.ForeignKey("users.id"), nullable=True)
    client_role = db.Column(enum_value_type(ClientRoleInCase, "client_role_case_enum"), nullable=False)
    fee_type = db.Column(enum_value_type(FeeType, "case_fee_type_enum"), nullable=False)
    agreed_fee_amount = db.Column(db.Numeric(14, 2), nullable=False)
    retainer_paid = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    payment_schedule = db.Column(JSON_TYPE, nullable=True)
    status = db.Column(enum_value_type(CaseStatus, "case_status_enum"), default=CaseStatus.NEW, nullable=False)
    priority = db.Column(enum_value_type(Priority, "case_priority_enum"), default=Priority.NORMAL, nullable=False)
    created_by = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HearingSession(db.Model, TimestampMixin):
    __tablename__ = "sessions"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id = db.Column(Uuid, db.ForeignKey("cases.id"), nullable=False, index=True)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    session_date = db.Column(db.Date, nullable=False)
    session_time = db.Column(db.Time, nullable=True)
    court = db.Column(db.String(255), nullable=True)
    court_circuit = db.Column(db.String(255), nullable=True)
    session_type = db.Column(enum_value_type(SessionType, "session_type_enum"), nullable=False)
    preparation_notes = db.Column(db.Text, nullable=True)
    result = db.Column(enum_value_type(SessionResult, "session_result_enum"), nullable=True)
    result_notes = db.Column(db.Text, nullable=True)
    next_session_date = db.Column(db.Date, nullable=True)
    minutes_file_url = db.Column(db.String(1024), nullable=True)
    added_by = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False)


class Judgment(db.Model, TimestampMixin):
    __tablename__ = "judgments"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id = db.Column(Uuid, db.ForeignKey("cases.id"), nullable=False, index=True)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    judgment_date = db.Column(db.Date, nullable=False)
    court = db.Column(db.String(255), nullable=True)
    court_circuit = db.Column(db.String(255), nullable=True)
    judge_name = db.Column(db.String(255), nullable=True)
    judgment_type = db.Column(enum_value_type(JudgmentType, "judgment_type_enum"), nullable=False)
    result = db.Column(enum_value_type(JudgmentResult, "judgment_result_enum"), nullable=False)
    judgment_text = db.Column(db.Text, nullable=True)
    judgment_file_url = db.Column(db.String(1024), nullable=True)
    awarded_amount = db.Column(db.Numeric(14, 2), nullable=True)
    appeal_tracked = db.Column(db.Boolean, default=False, nullable=False)
    appeal_type = db.Column(enum_value_type(AppealType, "appeal_type_enum"), nullable=True)
    appeal_deadline = db.Column(db.Date, nullable=True)
    added_by = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False)


class AppealReminder(db.Model):
    __tablename__ = "appeal_reminders"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    judgment_id = db.Column(Uuid, db.ForeignKey("judgments.id"), nullable=False, index=True)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    remind_at = db.Column(db.DateTime, nullable=False)
    days_before = db.Column(db.Integer, nullable=False)
    sent = db.Column(db.Boolean, default=False, nullable=False)
    sent_at = db.Column(db.DateTime, nullable=True)


class EnforcementFile(db.Model, TimestampMixin):
    __tablename__ = "enforcement_files"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id = db.Column(Uuid, db.ForeignKey("cases.id"), nullable=False, index=True)
    judgment_id = db.Column(Uuid, db.ForeignKey("judgments.id"), nullable=True, index=True)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    official_enforcement_number = db.Column(db.String(120), nullable=False)
    enforcement_court = db.Column(db.String(255), nullable=False)
    enforcement_officer = db.Column(db.String(255), nullable=True)
    enforcement_type = db.Column(enum_value_type(EnforcementType, "enforcement_type_enum"), nullable=False)
    total_amount = db.Column(db.Numeric(14, 2), nullable=False)
    collected_amount = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    debtor_name = db.Column(db.String(255), nullable=False)
    debtor_details = db.Column(JSON_TYPE, nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    status = db.Column(enum_value_type(EnforcementStatus, "enforcement_status_enum"), default=EnforcementStatus.ACTIVE)


class EnforcementPayment(db.Model):
    __tablename__ = "enforcement_payments"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    enforcement_id = db.Column(Uuid, db.ForeignKey("enforcement_files.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    collected_at = db.Column(db.Date, nullable=False)
    method = db.Column(db.String(80), nullable=False)
    notes = db.Column(db.Text, nullable=True)


class PowerOfAttorney(db.Model, TimestampMixin):
    __tablename__ = "powers_of_attorney"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id = db.Column(Uuid, db.ForeignKey("clients.id"), nullable=False, index=True)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    poa_type = db.Column(enum_value_type(PoaType, "poa_type_enum"), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)
    notary_office = db.Column(db.String(255), nullable=True)
    notary_number = db.Column(db.String(120), nullable=True)
    linked_case_id = db.Column(Uuid, db.ForeignKey("cases.id"), nullable=True)
    status = db.Column(enum_value_type(PoaStatus, "poa_status_enum"), default=PoaStatus.ACTIVE, nullable=False)
    responsible_lawyer_id = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False)


class Payment(db.Model, TimestampMixin):
    __tablename__ = "payments"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    client_id = db.Column(Uuid, db.ForeignKey("clients.id"), nullable=False, index=True)
    case_id = db.Column(Uuid, db.ForeignKey("cases.id"), nullable=True, index=True)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(enum_value_type(PaymentMethod, "payment_method_enum"), nullable=False)
    reference_number = db.Column(db.String(120), nullable=True)
    receipt_file_url = db.Column(db.String(1024), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    recorded_by = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False)


class Invoice(db.Model, TimestampMixin):
    __tablename__ = "invoices"
    __table_args__ = (db.UniqueConstraint("office_id", "invoice_number", name="uq_invoice_number_per_office"),)

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    client_id = db.Column(Uuid, db.ForeignKey("clients.id"), nullable=False, index=True)
    case_id = db.Column(Uuid, db.ForeignKey("cases.id"), nullable=True, index=True)
    invoice_number = db.Column(db.String(120), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    line_items = db.Column(JSON_TYPE, nullable=False, default=list)
    subtotal = db.Column(db.Numeric(14, 2), nullable=False)
    discount_type = db.Column(enum_value_type(DiscountType, "discount_type_enum"), nullable=True)
    discount_value = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    tax_enabled = db.Column(db.Boolean, default=True, nullable=False)
    tax_rate = db.Column(db.Numeric(6, 4), default=0.14, nullable=False)
    tax_amount = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    total = db.Column(db.Numeric(14, 2), nullable=False)
    status = db.Column(enum_value_type(InvoiceStatus, "invoice_status_enum"), default=InvoiceStatus.DRAFT, nullable=False)
    created_by = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False)


class Expense(db.Model, TimestampMixin):
    __tablename__ = "expenses"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    case_id = db.Column(Uuid, db.ForeignKey("cases.id"), nullable=False, index=True)
    client_id = db.Column(Uuid, db.ForeignKey("clients.id"), nullable=False, index=True)
    expense_type = db.Column(enum_value_type(ExpenseType, "expense_type_enum"), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    receipt_url = db.Column(db.String(1024), nullable=True)
    description = db.Column(db.Text, nullable=True)
    recorded_by = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False)


class Task(db.Model, TimestampMixin):
    __tablename__ = "tasks"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    assigned_to = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False)
    assigned_by = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False)
    case_id = db.Column(Uuid, db.ForeignKey("cases.id"), nullable=True, index=True)
    priority = db.Column(enum_value_type(TaskPriority, "task_priority_enum"), default=TaskPriority.NORMAL, nullable=False)
    status = db.Column(enum_value_type(TaskStatus, "task_status_enum"), default=TaskStatus.NEW, nullable=False)
    deadline = db.Column(db.DateTime, nullable=True)
    is_recurring = db.Column(db.Boolean, default=False, nullable=False)
    recurrence_type = db.Column(enum_value_type(RecurrenceType, "task_recurrence_enum"), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClientAppointment(db.Model, TimestampMixin):
    __tablename__ = "client_appointments"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    client_id = db.Column(Uuid, db.ForeignKey("clients.id"), nullable=False, index=True)
    lawyer_id = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    attendance_status = db.Column(
        enum_value_type(AttendanceStatus, "attendance_status_enum"),
        default=AttendanceStatus.PENDING,
        nullable=False,
    )


class Document(db.Model, TimestampMixin):
    __tablename__ = "documents"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    entity_type = db.Column(enum_value_type(EntityType, "document_entity_type_enum"), nullable=False)
    entity_id = db.Column(Uuid, nullable=False, index=True)
    doc_type = db.Column(enum_value_type(GlobalDocumentType, "global_document_type_enum"), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(1024), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(120), nullable=False)
    uploaded_by = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False)
    ai_summary = db.Column(db.Text, nullable=True)
    ai_summary_requested_at = db.Column(db.DateTime, nullable=True)


class Notification(db.Model, TimestampMixin):
    __tablename__ = "notifications"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    user_id = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False, index=True)
    type = db.Column(db.String(120), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    data = db.Column(JSON_TYPE, nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    sent_push = db.Column(db.Boolean, default=False, nullable=False)
    sent_email = db.Column(db.Boolean, default=False, nullable=False)
    sent_sms = db.Column(db.Boolean, default=False, nullable=False)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    user_id = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False, index=True)
    action = db.Column(db.String(20), nullable=False)
    entity_type = db.Column(db.String(120), nullable=False)
    entity_id = db.Column(Uuid, nullable=False)
    old_value = db.Column(JSON_TYPE, nullable=True)
    new_value = db.Column(JSON_TYPE, nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class LegalTemplate(db.Model, TimestampMixin):
    __tablename__ = "legal_templates"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=True, index=True)
    name = db.Column(db.String(255), nullable=False)
    template_type = db.Column(enum_value_type(TemplateType, "template_type_enum"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class CaseNote(db.Model, TimestampMixin):
    __tablename__ = "case_notes"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    case_id = db.Column(Uuid, db.ForeignKey("cases.id"), nullable=False, index=True)
    note = db.Column(db.Text, nullable=False)
    added_by = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False)


class MemberInvite(db.Model, TimestampMixin):
    __tablename__ = "member_invites"

    id = db.Column(Uuid, primary_key=True, default=uuid.uuid4)
    office_id = db.Column(Uuid, db.ForeignKey("offices.id"), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    role = db.Column(enum_value_type(UserRole, "invite_role_enum"), nullable=False)
    token = db.Column(db.String(255), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    accepted = db.Column(db.Boolean, default=False, nullable=False)
    invited_by = db.Column(Uuid, db.ForeignKey("users.id"), nullable=False)
