from marshmallow import EXCLUDE, Schema, fields, validate


class BaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE


class RegisterSchema(BaseSchema):
    office_name = fields.String(required=True)
    full_name = fields.String(required=True)
    email = fields.Email(required=True)
    phone = fields.String(required=True)
    password = fields.String(required=True)


class VerifyOtpSchema(BaseSchema):
    email = fields.Email(required=True)
    otp = fields.String(required=True)


class LoginSchema(BaseSchema):
    email = fields.Email(required=True)
    password = fields.String(required=True)
    mfa_code = fields.String(load_default=None)
    device_name = fields.String(load_default=None)
    device_type = fields.String(load_default=None)


class RefreshSchema(BaseSchema):
    refresh_token = fields.String(required=True)


class ForgotPasswordSchema(BaseSchema):
    email = fields.Email(required=True)


class ResetPasswordSchema(BaseSchema):
    email = fields.Email(required=True)
    otp = fields.String(required=True)
    new_password = fields.String(required=True)


class SetupOfficeSchema(BaseSchema):
    name = fields.String(required=True)
    logo_url = fields.String(load_default=None)
    address = fields.String(load_default=None)
    bar_association_number = fields.String(load_default=None)
    primary_courts = fields.List(fields.String(), load_default=[])
    official_phone = fields.String(load_default=None)
    fax = fields.String(load_default=None)
    official_email = fields.Email(load_default=None)


class PlanSchema(BaseSchema):
    subscription_plan = fields.String(
        required=True,
        validate=validate.OneOf(["starter", "professional", "enterprise"]),
    )


class InviteMemberSchema(BaseSchema):
    emails = fields.List(fields.Email(), required=True)
    role = fields.String(required=True)


class AcceptInviteSchema(BaseSchema):
    token = fields.String(required=True)
    full_name = fields.String(required=True)
    phone = fields.String(required=True)
    password = fields.String(required=True)


class OfficeUpdateSchema(SetupOfficeSchema):
    pass


class MemberRoleUpdateSchema(BaseSchema):
    role = fields.String(required=True)


class UserProfileUpdateSchema(BaseSchema):
    full_name = fields.String(load_default=None)
    phone = fields.String(load_default=None)
    profile_picture_url = fields.String(load_default=None)


class PasswordChangeSchema(BaseSchema):
    old_password = fields.String(required=True)
    new_password = fields.String(required=True)


class NotificationPrefSchema(BaseSchema):
    preferences = fields.Dict(required=True)


class QuietHoursSchema(BaseSchema):
    quiet_hours_start = fields.String(required=True)
    quiet_hours_end = fields.String(required=True)


class ClientSchema(BaseSchema):
    client_type = fields.String(required=True)
    full_name_ar = fields.String(required=True)
    full_name_en = fields.String(load_default=None)
    national_id_or_commercial_reg = fields.String(required=True)
    date_of_birth_or_founding = fields.Date(load_default=None)
    nationality = fields.String(load_default=None)
    profession_or_activity = fields.String(load_default=None)
    governorate = fields.String(load_default=None)
    city = fields.String(load_default=None)
    district = fields.String(load_default=None)
    street = fields.String(load_default=None)
    building_number = fields.String(load_default=None)
    primary_phone = fields.String(required=True)
    secondary_phone = fields.String(load_default=None)
    email = fields.Email(load_default=None)
    whatsapp = fields.String(load_default=None)
    emergency_contact_name = fields.String(load_default=None)
    emergency_contact_phone = fields.String(load_default=None)
    emergency_contact_relation = fields.String(load_default=None)
    internal_notes = fields.String(load_default=None)
    assigned_lawyer_id = fields.UUID(load_default=None)


class CaseSchema(BaseSchema):
    case_number = fields.String(required=True)
    case_year = fields.Integer(load_default=None)
    client_id = fields.UUID(required=True)
    court = fields.String(required=True)
    court_circuit = fields.String(load_default=None)
    case_type = fields.String(required=True)
    case_subject = fields.String(load_default=None)
    defendant_name = fields.String(load_default=None)
    defendant_lawyer = fields.String(load_default=None)
    responsible_lawyer_id = fields.UUID(required=True)
    assistant_lawyer_id = fields.UUID(load_default=None)
    client_role = fields.String(required=True)
    fee_type = fields.String(required=True)
    agreed_fee_amount = fields.Decimal(required=True, as_string=True)
    retainer_paid = fields.Decimal(load_default=0, as_string=True)
    payment_schedule = fields.Dict(load_default=None)
    status = fields.String(load_default="new")
    priority = fields.String(load_default="normal")


class CaseStatusSchema(BaseSchema):
    status = fields.String(required=True)


class SessionSchema(BaseSchema):
    case_id = fields.UUID(required=True)
    session_date = fields.Date(required=True)
    session_time = fields.Time(load_default=None)
    court = fields.String(load_default=None)
    court_circuit = fields.String(load_default=None)
    session_type = fields.String(required=True)
    preparation_notes = fields.String(load_default=None)


class SessionResultSchema(BaseSchema):
    result = fields.String(required=True)
    result_notes = fields.String(load_default=None)
    next_session_date = fields.Date(load_default=None)


class JudgmentSchema(BaseSchema):
    case_id = fields.UUID(required=True)
    judgment_date = fields.Date(required=True)
    court = fields.String(load_default=None)
    court_circuit = fields.String(load_default=None)
    judge_name = fields.String(load_default=None)
    judgment_type = fields.String(required=True)
    result = fields.String(required=True)
    judgment_text = fields.String(load_default=None)
    judgment_file_url = fields.String(load_default=None)
    awarded_amount = fields.Decimal(load_default=None, as_string=True)
    appeal_type = fields.String(load_default=None)
    appeal_deadline = fields.Date(load_default=None)


class TrackAppealSchema(BaseSchema):
    appeal_type = fields.String(required=True)
    appeal_deadline = fields.Date(required=True)


class EnforcementSchema(BaseSchema):
    case_id = fields.UUID(required=True)
    judgment_id = fields.UUID(load_default=None)
    official_enforcement_number = fields.String(required=True)
    enforcement_court = fields.String(required=True)
    enforcement_officer = fields.String(load_default=None)
    enforcement_type = fields.String(required=True)
    total_amount = fields.Decimal(required=True, as_string=True)
    debtor_name = fields.String(required=True)
    debtor_details = fields.Dict(load_default={})
    start_date = fields.Date(required=True)
    status = fields.String(load_default="active")


class EnforcementPaymentSchema(BaseSchema):
    amount = fields.Decimal(required=True, as_string=True)
    collected_at = fields.Date(required=True)
    method = fields.String(required=True)
    notes = fields.String(load_default=None)


class PoaSchema(BaseSchema):
    client_id = fields.UUID(required=True)
    poa_type = fields.String(required=True)
    issue_date = fields.Date(required=True)
    expiry_date = fields.Date(load_default=None)
    notary_office = fields.String(load_default=None)
    notary_number = fields.String(load_default=None)
    linked_case_id = fields.UUID(load_default=None)
    status = fields.String(load_default="active")
    responsible_lawyer_id = fields.UUID(required=True)


class PaymentSchema(BaseSchema):
    client_id = fields.UUID(required=True)
    case_id = fields.UUID(load_default=None)
    amount = fields.Decimal(required=True, as_string=True)
    payment_date = fields.Date(required=True)
    payment_method = fields.String(required=True)
    reference_number = fields.String(load_default=None)
    receipt_file_url = fields.String(load_default=None)
    notes = fields.String(load_default=None)


class InvoiceSchema(BaseSchema):
    client_id = fields.UUID(required=True)
    case_id = fields.UUID(load_default=None)
    issue_date = fields.Date(required=True)
    due_date = fields.Date(load_default=None)
    line_items = fields.List(fields.Dict(), required=True)
    subtotal = fields.Decimal(required=True, as_string=True)
    discount_type = fields.String(load_default=None)
    discount_value = fields.Decimal(load_default=0, as_string=True)
    tax_enabled = fields.Boolean(load_default=True)
    tax_rate = fields.Decimal(load_default="0.14", as_string=True)
    status = fields.String(load_default="draft")


class InvoiceStatusSchema(BaseSchema):
    status = fields.String(required=True)


class ExpenseSchema(BaseSchema):
    case_id = fields.UUID(required=True)
    client_id = fields.UUID(required=True)
    expense_type = fields.String(required=True)
    amount = fields.Decimal(required=True, as_string=True)
    expense_date = fields.Date(required=True)
    receipt_url = fields.String(load_default=None)
    description = fields.String(load_default=None)


class TaskSchema(BaseSchema):
    title = fields.String(required=True)
    description = fields.String(load_default=None)
    assigned_to = fields.UUID(required=True)
    case_id = fields.UUID(load_default=None)
    priority = fields.String(load_default="normal")
    status = fields.String(load_default="new")
    deadline = fields.DateTime(load_default=None)
    is_recurring = fields.Boolean(load_default=False)
    recurrence_type = fields.String(load_default=None)


class TaskStatusSchema(BaseSchema):
    status = fields.String(required=True)


class AppointmentSchema(BaseSchema):
    client_id = fields.UUID(required=True)
    lawyer_id = fields.UUID(required=True)
    appointment_date = fields.DateTime(required=True)
    notes = fields.String(load_default=None)


class AppointmentAttendanceSchema(BaseSchema):
    attendance_status = fields.String(required=True)


class DocumentUploadSchema(BaseSchema):
    entity_type = fields.String(required=True)
    entity_id = fields.UUID(required=True)
    doc_type = fields.String(required=True)
    doc_name = fields.String(load_default=None)


class TemplateSchema(BaseSchema):
    name = fields.String(required=True)
    template_type = fields.String(required=True)
    content = fields.String(required=True)
    is_active = fields.Boolean(load_default=True)


class TemplateGenerateSchema(BaseSchema):
    client_id = fields.UUID(required=True)
    case_id = fields.UUID(load_default=None)
    overrides = fields.Dict(load_default={})


class AISummaryRequestSchema(BaseSchema):
    document_id = fields.UUID(required=True)


class NotesSchema(BaseSchema):
    note = fields.String(required=True)
