from enum import Enum


class SubscriptionPlan(str, Enum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class UserRole(str, Enum):
    OWNER = "owner"
    PARTNER = "partner"
    SENIOR_LAWYER = "senior_lawyer"
    JUNIOR_LAWYER = "junior_lawyer"
    ASSISTANT = "assistant"
    ACCOUNTANT = "accountant"


class ClientType(str, Enum):
    INDIVIDUAL = "individual"
    COMPANY = "company"
    GOVERNMENT = "government"


class ClientDocumentType(str, Enum):
    NATIONAL_ID_FRONT = "national_id_front"
    NATIONAL_ID_BACK = "national_id_back"
    PASSPORT = "passport"
    COMMERCIAL_REG = "commercial_reg"
    TAX_CARD = "tax_card"
    OTHER = "other"


class CaseType(str, Enum):
    CRIMINAL = "criminal"
    CIVIL = "civil"
    COMMERCIAL = "commercial"
    ADMINISTRATIVE = "administrative"
    LABOR = "labor"
    FAMILY = "family"
    CONSTITUTIONAL = "constitutional"
    ENFORCEMENT = "enforcement"


class ClientRoleInCase(str, Enum):
    PLAINTIFF = "plaintiff"
    DEFENDANT = "defendant"
    APPELLANT = "appellant"
    APPELLEE = "appellee"
    OTHER = "other"


class FeeType(str, Enum):
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    HOURLY = "hourly"
    MIXED = "mixed"


class CaseStatus(str, Enum):
    NEW = "new"
    ACTIVE = "active"
    AWAITING_JUDGMENT = "awaiting_judgment"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class Priority(str, Enum):
    NORMAL = "normal"
    IMPORTANT = "important"
    CRITICAL = "critical"


class SessionType(str, Enum):
    FIRST = "first"
    PROOF = "proof"
    PLEADING = "pleading"
    JUDGMENT = "judgment"
    EMERGENCY = "emergency"
    POSTPONEMENT = "postponement"


class SessionResult(str, Enum):
    POSTPONED = "postponed"
    JUDGMENT = "judgment"
    DECISION = "decision"
    PROOF = "proof"
    ATTENDED_ABSENT = "attended_absent"


class JudgmentType(str, Enum):
    PRIMARY = "primary"
    APPELLATE = "appellate"
    CASSATION = "cassation"
    CONSTITUTIONAL = "constitutional"


class JudgmentResult(str, Enum):
    FULL_WIN = "full_win"
    PARTIAL_WIN = "partial_win"
    LOSS = "loss"
    POSTPONED = "postponed"
    FORMAL = "formal"


class AppealType(str, Enum):
    APPEAL = "appeal"
    CASSATION = "cassation"


class EnforcementType(str, Enum):
    REAL_ESTATE_SEIZURE = "real_estate_seizure"
    MONEY_SEIZURE = "money_seizure"
    MOVABLES_SEIZURE = "movables_seizure"
    EVICTION = "eviction"
    DELIVERY = "delivery"


class EnforcementStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    SUSPENDED = "suspended"


class PoaType(str, Enum):
    GENERAL = "general"
    SPECIFIC = "specific"
    JUDICIAL = "judicial"
    BANKING = "banking"
    REAL_ESTATE = "real_estate"
    COMMERCIAL = "commercial"


class PoaStatus(str, Enum):
    ACTIVE = "active"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"


class PaymentMethod(str, Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CHECK = "check"
    VODAFONE_CASH = "vodafone_cash"
    CARD = "card"


class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"


class ExpenseType(str, Enum):
    COURT_FEES = "court_fees"
    TRANSPORT = "transport"
    STAMP = "stamp"
    EXPERT = "expert"
    OTHER = "other"


class TaskPriority(str, Enum):
    URGENT = "urgent"
    IMPORTANT = "important"
    NORMAL = "normal"


class TaskStatus(str, Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class RecurrenceType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class AttendanceStatus(str, Enum):
    PENDING = "pending"
    ATTENDED = "attended"
    ABSENT = "absent"
    POSTPONED = "postponed"


class EntityType(str, Enum):
    CLIENT = "client"
    CASE = "case"
    SESSION = "session"


class GlobalDocumentType(str, Enum):
    DEFENSE_MEMO = "defense_memo"
    JUDGMENT = "judgment"
    CONTRACT = "contract"
    POA = "poa"
    RECEIPT = "receipt"
    CORRESPONDENCE = "correspondence"
    SESSION_MINUTES = "session_minutes"
    OTHER = "other"


class TemplateType(str, Enum):
    FEE_CONTRACT = "fee_contract"
    POA_SPECIFIC = "poa_specific"
    RECEIPT = "receipt"
    DEFENSE_MEMO = "defense_memo"
    CLIENT_LETTER = "client_letter"
