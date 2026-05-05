from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import (
    ActiveSession,
    AppealReminder,
    AuditLog,
    Case,
    CaseNote,
    Client,
    ClientAppointment,
    ClientDocument,
    Document,
    EnforcementFile,
    EnforcementPayment,
    Expense,
    HearingSession,
    Invoice,
    Judgment,
    LegalTemplate,
    MemberInvite,
    Notification,
    Office,
    Payment,
    PowerOfAttorney,
    Task,
    User,
)
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
from app.services.meta_data import get_egyptian_courts
from app.utils.security import hash_password

DEMO_PASSWORD = "Admin@123"
DEMO_OFFICE_BAR_PREFIX = "DEMO-LEXOFFICE-"

DEFAULT_TEMPLATES = [
    {
        "name": "Fee Contract Basic",
        "template_type": TemplateType.FEE_CONTRACT,
        "content": "Fee agreement between {{lawyer_name}} and {{client_name}} for case {{case_number}}.",
    },
    {
        "name": "Specific POA",
        "template_type": TemplateType.POA_SPECIFIC,
        "content": "Specific POA granted to {{lawyer_name}} by {{client_name}}.",
    },
    {
        "name": "Receipt",
        "template_type": TemplateType.RECEIPT,
        "content": "Receipt for amount collected from {{client_name}} on {{date}}.",
    },
    {
        "name": "Defense Memo",
        "template_type": TemplateType.DEFENSE_MEMO,
        "content": "Defense memo for case {{case_number}} before {{court}}.",
    },
    {
        "name": "Client Letter",
        "template_type": TemplateType.CLIENT_LETTER,
        "content": "Client letter to {{client_name}} regarding {{case_subject}}.",
    },
]

OFFICE_SPECS = [
    {
        "code": "CAI",
        "name": "LexOffice Demo - Cairo",
        "bar_number": f"{DEMO_OFFICE_BAR_PREFIX}CAIRO-001",
        "address": "12 Tahrir St, Downtown, Cairo",
        "phone": "+20211110001",
        "email": "office.cairo@demo.lexoffice",
        "plan": SubscriptionPlan.ENTERPRISE,
        "status": SubscriptionStatus.ACTIVE,
        "user_prefix": "cairo",
        "admin_email": "admin@demo.lexoffice",
        "courts_idx": [0, 1, 8],
    },
    {
        "code": "ALX",
        "name": "LexOffice Demo - Alexandria",
        "bar_number": f"{DEMO_OFFICE_BAR_PREFIX}ALEX-001",
        "address": "18 El Horreya Rd, Alexandria",
        "phone": "+20322220002",
        "email": "office.alex@demo.lexoffice",
        "plan": SubscriptionPlan.PROFESSIONAL,
        "status": SubscriptionStatus.ACTIVE,
        "user_prefix": "alex",
        "admin_email": "owner.alex@demo.lexoffice",
        "courts_idx": [2, 3, 9],
    },
]


def _notification_preferences():
    return {
        "session_reminder": {"push": True, "email": True, "sms": False},
        "appeal_deadline": {"push": True, "email": True, "sms": True},
        "task_overdue": {"push": True, "email": True, "sms": False},
        "payment_overdue": {"push": True, "email": True, "sms": False},
        "poa_expiry": {"push": True, "email": True, "sms": False},
        "daily_digest": {"push": False, "email": True, "sms": False},
    }


def _seed_default_templates() -> int:
    created = 0
    for item in DEFAULT_TEMPLATES:
        existing = LegalTemplate.query.filter_by(office_id=None, name=item["name"]).first()
        if existing:
            continue
        db.session.add(
            LegalTemplate(
                office_id=None,
                name=item["name"],
                template_type=item["template_type"].value,
                content=item["content"],
                is_active=True,
            )
        )
        created += 1
    return created


def _purge_existing_demo_data() -> int:
    demo_offices = Office.query.filter(Office.bar_association_number.like(f"{DEMO_OFFICE_BAR_PREFIX}%")).all()
    if not demo_offices:
        return 0

    office_ids = [office.id for office in demo_offices]
    user_ids = [user.id for user in User.query.filter(User.office_id.in_(office_ids)).all()]
    enforcement_ids = [row.id for row in EnforcementFile.query.filter(EnforcementFile.office_id.in_(office_ids)).all()]

    if enforcement_ids:
        EnforcementPayment.query.filter(EnforcementPayment.enforcement_id.in_(enforcement_ids)).delete(
            synchronize_session=False
        )
    if user_ids:
        ActiveSession.query.filter(ActiveSession.user_id.in_(user_ids)).delete(synchronize_session=False)

    AuditLog.query.filter(AuditLog.office_id.in_(office_ids)).delete(synchronize_session=False)
    Notification.query.filter(Notification.office_id.in_(office_ids)).delete(synchronize_session=False)
    Document.query.filter(Document.office_id.in_(office_ids)).delete(synchronize_session=False)
    ClientAppointment.query.filter(ClientAppointment.office_id.in_(office_ids)).delete(synchronize_session=False)
    Task.query.filter(Task.office_id.in_(office_ids)).delete(synchronize_session=False)
    Expense.query.filter(Expense.office_id.in_(office_ids)).delete(synchronize_session=False)
    Invoice.query.filter(Invoice.office_id.in_(office_ids)).delete(synchronize_session=False)
    Payment.query.filter(Payment.office_id.in_(office_ids)).delete(synchronize_session=False)
    PowerOfAttorney.query.filter(PowerOfAttorney.office_id.in_(office_ids)).delete(synchronize_session=False)
    AppealReminder.query.filter(AppealReminder.office_id.in_(office_ids)).delete(synchronize_session=False)
    Judgment.query.filter(Judgment.office_id.in_(office_ids)).delete(synchronize_session=False)
    HearingSession.query.filter(HearingSession.office_id.in_(office_ids)).delete(synchronize_session=False)
    CaseNote.query.filter(CaseNote.office_id.in_(office_ids)).delete(synchronize_session=False)
    EnforcementFile.query.filter(EnforcementFile.office_id.in_(office_ids)).delete(synchronize_session=False)
    Case.query.filter(Case.office_id.in_(office_ids)).delete(synchronize_session=False)
    ClientDocument.query.filter(ClientDocument.office_id.in_(office_ids)).delete(synchronize_session=False)
    MemberInvite.query.filter(MemberInvite.office_id.in_(office_ids)).delete(synchronize_session=False)
    LegalTemplate.query.filter(LegalTemplate.office_id.in_(office_ids)).delete(synchronize_session=False)
    Client.query.filter(Client.office_id.in_(office_ids)).delete(synchronize_session=False)
    User.query.filter(User.office_id.in_(office_ids)).delete(synchronize_session=False)
    Office.query.filter(Office.id.in_(office_ids)).delete(synchronize_session=False)

    db.session.commit()
    return len(office_ids)


def _create_user(
    office_id,
    full_name: str,
    email: str,
    phone: str,
    role: UserRole,
    *,
    daily_digest: bool = False,
    mfa_enabled: bool = False,
):
    user = User(
        office_id=office_id,
        full_name=full_name,
        email=email,
        phone=phone,
        password_hash=hash_password(DEMO_PASSWORD),
        role=role.value,
        is_active=True,
        mfa_enabled=mfa_enabled,
        notification_preferences=_notification_preferences(),
        quiet_hours_start=time(22, 0),
        quiet_hours_end=time(8, 0),
        daily_digest_enabled=daily_digest,
    )
    db.session.add(user)
    db.session.flush()
    return user


def _seed_office(spec: dict, courts: list[str]) -> dict:
    now = datetime.utcnow()
    phone_seed = "31" if spec["code"] == "CAI" else "52"
    summary = {
        "offices": 0,
        "users": 0,
        "clients": 0,
        "cases": 0,
        "sessions": 0,
        "judgments": 0,
        "invoices": 0,
        "tasks": 0,
        "documents": 0,
    }

    office = Office(
        name=spec["name"],
        address=spec["address"],
        bar_association_number=spec["bar_number"],
        official_phone=spec["phone"],
        official_email=spec["email"],
        primary_courts=[courts[i % len(courts)] for i in spec["courts_idx"]],
        subscription_plan=spec["plan"].value,
        subscription_status=spec["status"].value,
        trial_ends_at=now + timedelta(days=30),
    )
    db.session.add(office)
    db.session.flush()
    summary["offices"] += 1

    owner = _create_user(
        office.id,
        f"{spec['code']} Office Admin",
        spec["admin_email"],
        f"+20111{phone_seed}00001",
        UserRole.OWNER,
        daily_digest=True,
        mfa_enabled=True,
    )
    partner = _create_user(
        office.id,
        f"{spec['code']} Senior Partner",
        f"partner.{spec['user_prefix']}@demo.lexoffice",
        f"+20111{phone_seed}00002",
        UserRole.PARTNER,
        daily_digest=True,
    )
    senior = _create_user(
        office.id,
        f"{spec['code']} Senior Lawyer",
        f"senior.{spec['user_prefix']}@demo.lexoffice",
        f"+20111{phone_seed}00003",
        UserRole.SENIOR_LAWYER,
    )
    junior = _create_user(
        office.id,
        f"{spec['code']} Junior Lawyer",
        f"junior.{spec['user_prefix']}@demo.lexoffice",
        f"+20111{phone_seed}00004",
        UserRole.JUNIOR_LAWYER,
    )
    assistant = _create_user(
        office.id,
        f"{spec['code']} Legal Assistant",
        f"assistant.{spec['user_prefix']}@demo.lexoffice",
        f"+20111{phone_seed}00005",
        UserRole.ASSISTANT,
    )
    accountant = _create_user(
        office.id,
        f"{spec['code']} Accountant",
        f"accountant.{spec['user_prefix']}@demo.lexoffice",
        f"+20111{phone_seed}00006",
        UserRole.ACCOUNTANT,
    )
    summary["users"] += 6

    db.session.add_all(
        [
            ActiveSession(
                user_id=owner.id,
                device_name="Chrome on Windows",
                device_type="web",
                ip_address="41.38.10.10",
                refresh_token_hash=f"{spec['code'].lower()}_owner_refresh_hash",
                last_active_at=now - timedelta(minutes=12),
                expires_at=now + timedelta(days=30),
            ),
            ActiveSession(
                user_id=partner.id,
                device_name="iPhone 15 Pro",
                device_type="mobile",
                ip_address="156.221.14.25",
                refresh_token_hash=f"{spec['code'].lower()}_partner_refresh_hash",
                last_active_at=now - timedelta(hours=2),
                expires_at=now + timedelta(days=30),
            ),
        ]
    )

    clients = [
        Client(
            office_id=office.id,
            client_number=f"CL-{spec['code']}-001",
            client_type=ClientType.COMPANY.value,
            full_name_ar="Al Mashreq Construction LLC",
            full_name_en="Al Mashreq Construction LLC",
            national_id_or_commercial_reg=f"{spec['code']}-CR-10001",
            date_of_birth_or_founding=date(2015, 6, 1),
            nationality="Egyptian",
            profession_or_activity="Construction",
            governorate="Cairo" if spec["code"] == "CAI" else "Alexandria",
            city="Nasr City" if spec["code"] == "CAI" else "Sidi Gaber",
            district="District 5",
            street="Business Avenue",
            building_number="14B",
            primary_phone="+201005550001",
            secondary_phone="+201005550011",
            email=f"contact.{spec['user_prefix']}@almashreq.com",
            whatsapp="+201005550001",
            emergency_contact_name="Company Hotline",
            emergency_contact_phone="+201005550099",
            emergency_contact_relation="Operations",
            internal_notes="High-value corporate client with ongoing arbitration and labor disputes.",
            assigned_lawyer_id=senior.id,
            created_by=owner.id,
        ),
        Client(
            office_id=office.id,
            client_number=f"CL-{spec['code']}-002",
            client_type=ClientType.INDIVIDUAL.value,
            full_name_ar="Mahmoud Hassan Ibrahim",
            full_name_en="Mahmoud Hassan Ibrahim",
            national_id_or_commercial_reg=f"{spec['code']}-NID-20002",
            date_of_birth_or_founding=date(1988, 9, 14),
            nationality="Egyptian",
            profession_or_activity="Business Owner",
            governorate="Cairo" if spec["code"] == "CAI" else "Alexandria",
            city="Heliopolis" if spec["code"] == "CAI" else "Gleem",
            district="District 2",
            street="Legal Plaza",
            building_number="9A",
            primary_phone="+201006660002",
            secondary_phone="+201006660022",
            email=f"mahmoud.{spec['user_prefix']}@example.com",
            whatsapp="+201006660002",
            emergency_contact_name="Sara Hassan",
            emergency_contact_phone="+201006660033",
            emergency_contact_relation="Spouse",
            internal_notes="Needs frequent updates by SMS for hearing schedule changes.",
            assigned_lawyer_id=junior.id,
            created_by=partner.id,
        ),
        Client(
            office_id=office.id,
            client_number=f"CL-{spec['code']}-003",
            client_type=ClientType.GOVERNMENT.value,
            full_name_ar="General Authority for Investment",
            full_name_en="General Authority for Investment",
            national_id_or_commercial_reg=f"{spec['code']}-GOV-30003",
            date_of_birth_or_founding=date(1997, 1, 1),
            nationality="Egyptian",
            profession_or_activity="Government Authority",
            governorate="Cairo",
            city="Cairo",
            district="Government District",
            street="Authority Road",
            building_number="1",
            primary_phone="16000",
            secondary_phone="+20224560000",
            email=f"gafi.{spec['user_prefix']}@gov.eg",
            whatsapp=None,
            emergency_contact_name="Main Desk",
            emergency_contact_phone="16000",
            emergency_contact_relation="Official",
            internal_notes="Requires formal report packet each month.",
            assigned_lawyer_id=partner.id,
            created_by=owner.id,
        ),
    ]
    db.session.add_all(clients)
    db.session.flush()
    summary["clients"] += len(clients)

    db.session.add_all(
        [
            ClientDocument(
                client_id=clients[0].id,
                office_id=office.id,
                doc_type=ClientDocumentType.COMMERCIAL_REG.value,
                file_url=f"storage/demo/{spec['code'].lower()}/clients/{clients[0].id}/commercial_reg.pdf",
                file_name="commercial_reg.pdf",
                uploaded_by=assistant.id,
            ),
            ClientDocument(
                client_id=clients[1].id,
                office_id=office.id,
                doc_type=ClientDocumentType.NATIONAL_ID_FRONT.value,
                file_url=f"storage/demo/{spec['code'].lower()}/clients/{clients[1].id}/national_id_front.jpg",
                file_name="national_id_front.jpg",
                uploaded_by=assistant.id,
            ),
            ClientDocument(
                client_id=clients[2].id,
                office_id=office.id,
                doc_type=ClientDocumentType.OTHER.value,
                file_url=f"storage/demo/{spec['code'].lower()}/clients/{clients[2].id}/authority_letter.pdf",
                file_name="authority_letter.pdf",
                uploaded_by=assistant.id,
            ),
        ]
    )

    cases = [
        Case(
            office_id=office.id,
            case_number=f"{spec['code']}-COM-2024-001",
            case_year=2024,
            client_id=clients[0].id,
            court=courts[spec["courts_idx"][0] % len(courts)],
            court_circuit="Circuit 12",
            case_type=CaseType.COMMERCIAL.value,
            case_subject="Breach of commercial supply contract with delayed payments.",
            defendant_name="Delta Trading Group",
            defendant_lawyer="Nader Farouk",
            responsible_lawyer_id=senior.id,
            assistant_lawyer_id=assistant.id,
            client_role=ClientRoleInCase.PLAINTIFF.value,
            fee_type=FeeType.FIXED.value,
            agreed_fee_amount=Decimal("125000.00"),
            retainer_paid=Decimal("40000.00"),
            payment_schedule=[
                {"milestone": "Case filing", "amount": 30000},
                {"milestone": "First hearing", "amount": 25000},
                {"milestone": "Judgment", "amount": 30000},
            ],
            status=CaseStatus.ACTIVE.value,
            priority=Priority.CRITICAL.value,
            created_by=partner.id,
        ),
        Case(
            office_id=office.id,
            case_number=f"{spec['code']}-LAB-2024-002",
            case_year=2024,
            client_id=clients[1].id,
            court=courts[spec["courts_idx"][1] % len(courts)],
            court_circuit="Circuit 7",
            case_type=CaseType.LABOR.value,
            case_subject="Unlawful termination and compensation claim.",
            defendant_name="Global Service Solutions",
            defendant_lawyer="Hany Saber",
            responsible_lawyer_id=junior.id,
            assistant_lawyer_id=assistant.id,
            client_role=ClientRoleInCase.PLAINTIFF.value,
            fee_type=FeeType.PERCENTAGE.value,
            agreed_fee_amount=Decimal("70000.00"),
            retainer_paid=Decimal("15000.00"),
            payment_schedule=[{"milestone": "Judgment", "amount": 55000}],
            status=CaseStatus.AWAITING_JUDGMENT.value,
            priority=Priority.IMPORTANT.value,
            created_by=owner.id,
        ),
        Case(
            office_id=office.id,
            case_number=f"{spec['code']}-ADM-2023-003",
            case_year=2023,
            client_id=clients[2].id,
            court=courts[spec["courts_idx"][2] % len(courts)],
            court_circuit="Administrative Chamber 2",
            case_type=CaseType.ADMINISTRATIVE.value,
            case_subject="Administrative challenge against public procurement decision.",
            defendant_name="Procurement Board",
            defendant_lawyer="Official Counsel",
            responsible_lawyer_id=partner.id,
            assistant_lawyer_id=senior.id,
            client_role=ClientRoleInCase.APPELLANT.value,
            fee_type=FeeType.MIXED.value,
            agreed_fee_amount=Decimal("180000.00"),
            retainer_paid=Decimal("60000.00"),
            payment_schedule=[
                {"milestone": "Case preparation", "amount": 40000},
                {"milestone": "Final decision", "amount": 80000},
            ],
            status=CaseStatus.SUSPENDED.value,
            priority=Priority.NORMAL.value,
            created_by=owner.id,
        ),
    ]
    db.session.add_all(cases)
    db.session.flush()
    summary["cases"] += len(cases)

    db.session.add_all(
        [
            CaseNote(
                office_id=office.id,
                case_id=cases[0].id,
                note="Client requested accelerated enforcement immediately after judgment.",
                added_by=senior.id,
            ),
            CaseNote(
                office_id=office.id,
                case_id=cases[1].id,
                note="Collect additional payroll evidence from witness before next hearing.",
                added_by=junior.id,
            ),
            CaseNote(
                office_id=office.id,
                case_id=cases[2].id,
                note="Board requested legal opinion memo before next filing window.",
                added_by=partner.id,
            ),
        ]
    )

    sessions = [
        HearingSession(
            case_id=cases[0].id,
            office_id=office.id,
            session_date=date.today() + timedelta(days=2),
            session_time=time(9, 0),
            court=cases[0].court,
            court_circuit=cases[0].court_circuit,
            session_type=SessionType.PLEADING.value,
            preparation_notes="Finalize witness statement packet and financial annex.",
            result=None,
            result_notes=None,
            next_session_date=None,
            minutes_file_url=None,
            added_by=assistant.id,
        ),
        HearingSession(
            case_id=cases[1].id,
            office_id=office.id,
            session_date=date.today() - timedelta(days=5),
            session_time=time(11, 30),
            court=cases[1].court,
            court_circuit=cases[1].court_circuit,
            session_type=SessionType.PROOF.value,
            preparation_notes="Prepare compensation worksheet and witness questions.",
            result=SessionResult.POSTPONED.value,
            result_notes="Postponed to submit missing payroll records.",
            next_session_date=date.today() + timedelta(days=9),
            minutes_file_url=f"storage/demo/{spec['code'].lower()}/sessions/minutes_1.pdf",
            added_by=assistant.id,
        ),
        HearingSession(
            case_id=cases[2].id,
            office_id=office.id,
            session_date=date.today() + timedelta(days=15),
            session_time=time(13, 0),
            court=cases[2].court,
            court_circuit=cases[2].court_circuit,
            session_type=SessionType.FIRST.value,
            preparation_notes="Review procurement committee minutes and draft opening argument.",
            result=None,
            result_notes=None,
            next_session_date=None,
            minutes_file_url=None,
            added_by=assistant.id,
        ),
    ]
    db.session.add_all(sessions)
    db.session.flush()
    summary["sessions"] += len(sessions)

    judgments = [
        Judgment(
            case_id=cases[0].id,
            office_id=office.id,
            judgment_date=date.today() - timedelta(days=18),
            court=cases[0].court,
            court_circuit=cases[0].court_circuit,
            judge_name="Counselor Ahmed Samir",
            judgment_type=JudgmentType.PRIMARY.value,
            result=JudgmentResult.FULL_WIN.value,
            judgment_text="Court awarded full contractual damages and legal fees.",
            judgment_file_url=f"storage/demo/{spec['code'].lower()}/judgments/judgment_1.pdf",
            awarded_amount=Decimal("120000.00"),
            appeal_tracked=True,
            appeal_type=AppealType.APPEAL.value,
            appeal_deadline=date.today() + timedelta(days=22),
            added_by=senior.id,
        ),
        Judgment(
            case_id=cases[1].id,
            office_id=office.id,
            judgment_date=date.today() - timedelta(days=6),
            court=cases[1].court,
            court_circuit=cases[1].court_circuit,
            judge_name="Counselor Mona Adel",
            judgment_type=JudgmentType.PRIMARY.value,
            result=JudgmentResult.PARTIAL_WIN.value,
            judgment_text="Partial compensation awarded pending appeal for remaining claims.",
            judgment_file_url=f"storage/demo/{spec['code'].lower()}/judgments/judgment_2.pdf",
            awarded_amount=Decimal("45000.00"),
            appeal_tracked=True,
            appeal_type=AppealType.APPEAL.value,
            appeal_deadline=date.today() + timedelta(days=11),
            added_by=junior.id,
        ),
    ]
    db.session.add_all(judgments)
    db.session.flush()
    summary["judgments"] += len(judgments)

    db.session.add_all(
        [
            AppealReminder(
                judgment_id=judgments[0].id,
                office_id=office.id,
                remind_at=now + timedelta(days=15),
                days_before=7,
                sent=False,
                sent_at=None,
            ),
            AppealReminder(
                judgment_id=judgments[1].id,
                office_id=office.id,
                remind_at=now + timedelta(days=8),
                days_before=3,
                sent=False,
                sent_at=None,
            ),
        ]
    )

    enforcement_file = EnforcementFile(
        case_id=cases[0].id,
        judgment_id=judgments[0].id,
        office_id=office.id,
        official_enforcement_number=f"ENF-{spec['code']}-001",
        enforcement_court=cases[0].court,
        enforcement_officer="Maher Zaki",
        enforcement_type=EnforcementType.MONEY_SEIZURE.value,
        total_amount=Decimal("120000.00"),
        collected_amount=Decimal("45000.00"),
        debtor_name="Delta Trading Group",
        debtor_details={"commercial_reg": "DR-779931", "address": "Smouha Business Park"},
        start_date=date.today() - timedelta(days=10),
        status=EnforcementStatus.ACTIVE.value,
    )
    db.session.add(enforcement_file)
    db.session.flush()

    db.session.add_all(
        [
            EnforcementPayment(
                enforcement_id=enforcement_file.id,
                amount=Decimal("25000.00"),
                collected_at=date.today() - timedelta(days=6),
                method=PaymentMethod.BANK_TRANSFER.value,
                notes="First transfer after enforcement warning notice.",
            ),
            EnforcementPayment(
                enforcement_id=enforcement_file.id,
                amount=Decimal("20000.00"),
                collected_at=date.today() - timedelta(days=2),
                method=PaymentMethod.CASH.value,
                notes="Second settlement installment.",
            ),
        ]
    )

    db.session.add_all(
        [
            PowerOfAttorney(
                client_id=clients[0].id,
                office_id=office.id,
                poa_type=PoaType.GENERAL.value,
                issue_date=date.today() - timedelta(days=300),
                expiry_date=date.today() + timedelta(days=420),
                notary_office="Heliopolis Notary",
                notary_number=f"POA-{spec['code']}-001",
                linked_case_id=cases[0].id,
                status=PoaStatus.ACTIVE.value,
                responsible_lawyer_id=senior.id,
            ),
            PowerOfAttorney(
                client_id=clients[1].id,
                office_id=office.id,
                poa_type=PoaType.JUDICIAL.value,
                issue_date=date.today() - timedelta(days=340),
                expiry_date=date.today() + timedelta(days=12),
                notary_office="Downtown Notary",
                notary_number=f"POA-{spec['code']}-002",
                linked_case_id=cases[1].id,
                status=PoaStatus.EXPIRING_SOON.value,
                responsible_lawyer_id=junior.id,
            ),
        ]
    )

    db.session.add_all(
        [
            Payment(
                office_id=office.id,
                client_id=clients[0].id,
                case_id=cases[0].id,
                amount=Decimal("30000.00"),
                payment_date=date.today() - timedelta(days=40),
                payment_method=PaymentMethod.BANK_TRANSFER.value,
                reference_number=f"PAY-{spec['code']}-0001",
                receipt_file_url=f"storage/demo/{spec['code'].lower()}/payments/pay_1.pdf",
                notes="Retainer installment 1.",
                recorded_by=accountant.id,
            ),
            Payment(
                office_id=office.id,
                client_id=clients[0].id,
                case_id=cases[0].id,
                amount=Decimal("10000.00"),
                payment_date=date.today() - timedelta(days=10),
                payment_method=PaymentMethod.CASH.value,
                reference_number=f"PAY-{spec['code']}-0002",
                receipt_file_url=f"storage/demo/{spec['code'].lower()}/payments/pay_2.pdf",
                notes="Supplementary cash payment.",
                recorded_by=accountant.id,
            ),
            Payment(
                office_id=office.id,
                client_id=clients[1].id,
                case_id=cases[1].id,
                amount=Decimal("15000.00"),
                payment_date=date.today() - timedelta(days=24),
                payment_method=PaymentMethod.CARD.value,
                reference_number=f"PAY-{spec['code']}-0003",
                receipt_file_url=f"storage/demo/{spec['code'].lower()}/payments/pay_3.pdf",
                notes="Labor case retainer.",
                recorded_by=accountant.id,
            ),
        ]
    )

    invoices = [
        Invoice(
            office_id=office.id,
            client_id=clients[0].id,
            case_id=cases[0].id,
            invoice_number=f"INV-{spec['code']}-001",
            issue_date=date.today() - timedelta(days=32),
            due_date=date.today() - timedelta(days=2),
            line_items=[
                {"description": "Commercial litigation service phase 1", "qty": 1, "unit_price": 60000},
            ],
            subtotal=Decimal("60000.00"),
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=Decimal("10.00"),
            tax_enabled=True,
            tax_rate=Decimal("0.14"),
            tax_amount=Decimal("7560.00"),
            total=Decimal("63560.00"),
            status=InvoiceStatus.OVERDUE.value,
            created_by=accountant.id,
        ),
        Invoice(
            office_id=office.id,
            client_id=clients[1].id,
            case_id=cases[1].id,
            invoice_number=f"INV-{spec['code']}-002",
            issue_date=date.today() - timedelta(days=15),
            due_date=date.today() + timedelta(days=10),
            line_items=[
                {"description": "Labor dispute representation", "qty": 1, "unit_price": 45000},
            ],
            subtotal=Decimal("45000.00"),
            discount_type=None,
            discount_value=Decimal("0.00"),
            tax_enabled=True,
            tax_rate=Decimal("0.14"),
            tax_amount=Decimal("6300.00"),
            total=Decimal("51300.00"),
            status=InvoiceStatus.SENT.value,
            created_by=accountant.id,
        ),
    ]
    db.session.add_all(invoices)
    summary["invoices"] += len(invoices)

    db.session.add_all(
        [
            Expense(
                office_id=office.id,
                case_id=cases[0].id,
                client_id=clients[0].id,
                expense_type=ExpenseType.COURT_FEES.value,
                amount=Decimal("4200.00"),
                expense_date=date.today() - timedelta(days=9),
                receipt_url=f"storage/demo/{spec['code'].lower()}/expenses/court_fees_1.pdf",
                description="Commercial court filing and stamps.",
                recorded_by=accountant.id,
            ),
            Expense(
                office_id=office.id,
                case_id=cases[1].id,
                client_id=clients[1].id,
                expense_type=ExpenseType.TRANSPORT.value,
                amount=Decimal("650.00"),
                expense_date=date.today() - timedelta(days=3),
                receipt_url=f"storage/demo/{spec['code'].lower()}/expenses/transport_1.pdf",
                description="Travel to labor court hearing and archive office.",
                recorded_by=assistant.id,
            ),
        ]
    )

    tasks = [
        Task(
            office_id=office.id,
            title="Review defense memo draft",
            description="Finalize argument structure and legal citations for commercial case.",
            assigned_to=senior.id,
            assigned_by=partner.id,
            case_id=cases[0].id,
            priority=TaskPriority.URGENT.value,
            status=TaskStatus.IN_PROGRESS.value,
            deadline=now + timedelta(hours=20),
            is_recurring=False,
            recurrence_type=None,
        ),
        Task(
            office_id=office.id,
            title="Collect witness statement",
            description="Coordinate with client witness and upload signed statement.",
            assigned_to=junior.id,
            assigned_by=senior.id,
            case_id=cases[1].id,
            priority=TaskPriority.IMPORTANT.value,
            status=TaskStatus.NEW.value,
            deadline=now + timedelta(days=2),
            is_recurring=False,
            recurrence_type=None,
        ),
        Task(
            office_id=office.id,
            title="Monthly invoice reconciliation",
            description="Reconcile payments, invoices, and overdue alerts.",
            assigned_to=accountant.id,
            assigned_by=owner.id,
            case_id=cases[0].id,
            priority=TaskPriority.NORMAL.value,
            status=TaskStatus.DONE.value,
            deadline=now - timedelta(days=1),
            is_recurring=True,
            recurrence_type=RecurrenceType.MONTHLY.value,
        ),
    ]
    db.session.add_all(tasks)
    summary["tasks"] += len(tasks)

    db.session.add_all(
        [
            ClientAppointment(
                office_id=office.id,
                client_id=clients[0].id,
                lawyer_id=senior.id,
                appointment_date=now + timedelta(days=1, hours=3),
                notes="Strategy meeting for enforcement actions.",
                attendance_status=AttendanceStatus.PENDING.value,
            ),
            ClientAppointment(
                office_id=office.id,
                client_id=clients[1].id,
                lawyer_id=junior.id,
                appointment_date=now - timedelta(days=4),
                notes="Review evidence package and compensation calculations.",
                attendance_status=AttendanceStatus.ATTENDED.value,
            ),
        ]
    )

    documents = [
        Document(
            office_id=office.id,
            entity_type=EntityType.CASE.value,
            entity_id=cases[0].id,
            doc_type=GlobalDocumentType.DEFENSE_MEMO.value,
            file_name="defense_memo_case_1.pdf",
            file_url=f"storage/demo/{spec['code'].lower()}/documents/case_1_defense_memo.pdf",
            file_size=248120,
            mime_type="application/pdf",
            uploaded_by=assistant.id,
            ai_summary="Defense memo summary: contract breach timeline, payment proof, and legal precedents.",
            ai_summary_requested_at=now - timedelta(days=2),
        ),
        Document(
            office_id=office.id,
            entity_type=EntityType.CLIENT.value,
            entity_id=clients[0].id,
            doc_type=GlobalDocumentType.CONTRACT.value,
            file_name="master_contract.pdf",
            file_url=f"storage/demo/{spec['code'].lower()}/documents/client_contract.pdf",
            file_size=132450,
            mime_type="application/pdf",
            uploaded_by=assistant.id,
            ai_summary=None,
            ai_summary_requested_at=None,
        ),
        Document(
            office_id=office.id,
            entity_type=EntityType.SESSION.value,
            entity_id=sessions[1].id,
            doc_type=GlobalDocumentType.SESSION_MINUTES.value,
            file_name="session_minutes.docx",
            file_url=f"storage/demo/{spec['code'].lower()}/documents/session_minutes.docx",
            file_size=64220,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            uploaded_by=assistant.id,
            ai_summary="Minutes mention postponement due to missing payroll records.",
            ai_summary_requested_at=now - timedelta(days=1),
        ),
    ]
    db.session.add_all(documents)
    summary["documents"] += len(documents)

    db.session.add_all(
        [
            Notification(
                office_id=office.id,
                user_id=owner.id,
                type="appeal_deadline",
                title="Appeal deadline in 7 days",
                body=f"Case {cases[0].case_number} appeal deadline approaching.",
                data={"case_id": str(cases[0].id), "judgment_id": str(judgments[0].id)},
                is_read=False,
                sent_push=False,
                sent_email=True,
                sent_sms=False,
            ),
            Notification(
                office_id=office.id,
                user_id=senior.id,
                type="session_reminder",
                title="Upcoming pleading session",
                body=f"Session scheduled for case {cases[0].case_number} in 2 days.",
                data={"case_id": str(cases[0].id), "session_id": str(sessions[0].id)},
                is_read=False,
                sent_push=True,
                sent_email=True,
                sent_sms=False,
            ),
            Notification(
                office_id=office.id,
                user_id=accountant.id,
                type="payment_overdue",
                title="Overdue invoice requires follow-up",
                body=f"Invoice {invoices[0].invoice_number} is overdue and needs client follow-up.",
                data={"invoice_id": str(invoices[0].id)},
                is_read=True,
                sent_push=True,
                sent_email=True,
                sent_sms=False,
            ),
        ]
    )

    db.session.add_all(
        [
            AuditLog(
                office_id=office.id,
                user_id=owner.id,
                action="create",
                entity_type="case",
                entity_id=cases[0].id,
                old_value=None,
                new_value={"status": CaseStatus.NEW.value, "priority": Priority.CRITICAL.value},
                ip_address="41.38.10.10",
            ),
            AuditLog(
                office_id=office.id,
                user_id=accountant.id,
                action="update",
                entity_type="invoice",
                entity_id=invoices[0].id,
                old_value={"status": InvoiceStatus.SENT.value},
                new_value={"status": InvoiceStatus.OVERDUE.value},
                ip_address="156.221.14.25",
            ),
        ]
    )

    db.session.add_all(
        [
            LegalTemplate(
                office_id=office.id,
                name=f"{spec['code']} - Client Intake Letter",
                template_type=TemplateType.CLIENT_LETTER.value,
                content="Dear {{client_name}}, please provide all supporting docs for case {{case_number}}.",
                is_active=True,
            ),
            LegalTemplate(
                office_id=office.id,
                name=f"{spec['code']} - Litigation Invoice",
                template_type=TemplateType.RECEIPT.value,
                content="Invoice for {{client_name}} - amount {{amount}} - case {{case_number}}.",
                is_active=True,
            ),
        ]
    )

    db.session.add_all(
        [
            MemberInvite(
                office_id=office.id,
                email=f"new.lawyer.{spec['user_prefix']}@demo.lexoffice",
                role=UserRole.JUNIOR_LAWYER.value,
                token=f"invite_{spec['code'].lower()}_junior_lawyer",
                expires_at=now + timedelta(days=7),
                accepted=False,
                invited_by=partner.id,
            ),
            MemberInvite(
                office_id=office.id,
                email=f"new.accountant.{spec['user_prefix']}@demo.lexoffice",
                role=UserRole.ACCOUNTANT.value,
                token=f"invite_{spec['code'].lower()}_accountant",
                expires_at=now + timedelta(days=5),
                accepted=False,
                invited_by=owner.id,
            ),
        ]
    )

    return summary


def run_seed():
    app = create_app()
    with app.app_context():
        removed_offices = _purge_existing_demo_data()
        templates_created = _seed_default_templates()

        courts = list(get_egyptian_courts())
        if len(courts) < 10:
            raise RuntimeError("Insufficient courts metadata for demo seeding.")

        summary_totals = {
            "offices": 0,
            "users": 0,
            "clients": 0,
            "cases": 0,
            "sessions": 0,
            "judgments": 0,
            "invoices": 0,
            "tasks": 0,
            "documents": 0,
        }

        for spec in OFFICE_SPECS:
            office_summary = _seed_office(spec, courts)
            for key, value in office_summary.items():
                summary_totals[key] += value

        db.session.commit()

        print("=== LexOffice demo data seeded successfully ===")
        print(f"Removed existing demo offices: {removed_offices}")
        print(f"Inserted global templates: {templates_created}")
        for key, value in summary_totals.items():
            print(f"Seeded {key}: {value}")
        print("Egyptian courts available from meta service:", len(courts))
        print("")
        print("Demo login credentials:")
        print(f"- Admin account: admin@demo.lexoffice / {DEMO_PASSWORD}")
        print("- Additional users follow pattern: <role>.<cairo|alex>@demo.lexoffice")


if __name__ == "__main__":
    run_seed()
