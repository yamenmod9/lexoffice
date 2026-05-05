from app import create_app
from app.extensions import db
from app.models import LegalTemplate
from app.models.enums import TemplateType
from app.services.meta_data import get_egyptian_courts

DEFAULT_TEMPLATES = [
    {
        "name": "Fee Contract Basic",
        "template_type": TemplateType.FEE_CONTRACT,
        "content": "اتفاق أتعاب بين {{lawyer_name}} و {{client_name}} بخصوص القضية {{case_number}}.",
    },
    {
        "name": "Specific POA",
        "template_type": TemplateType.POA_SPECIFIC,
        "content": "توكيل خاص لصالح {{lawyer_name}} عن {{client_name}}.",
    },
    {
        "name": "Receipt",
        "template_type": TemplateType.RECEIPT,
        "content": "إيصال استلام مبلغ من {{client_name}} بتاريخ {{date}}.",
    },
    {
        "name": "Defense Memo",
        "template_type": TemplateType.DEFENSE_MEMO,
        "content": "مذكرة دفاع في القضية {{case_number}} أمام {{court}}.",
    },
    {
        "name": "Client Letter",
        "template_type": TemplateType.CLIENT_LETTER,
        "content": "خطاب إلى العميل {{client_name}} بشأن {{case_subject}}.",
    },
]


def run_seed():
    app = create_app()
    with app.app_context():
        created = 0
        for item in DEFAULT_TEMPLATES:
            existing = LegalTemplate.query.filter_by(office_id=None, name=item["name"]).first()
            if existing:
                continue
            template = LegalTemplate(
                office_id=None,
                name=item["name"],
                template_type=item["template_type"],
                content=item["content"],
                is_active=True,
            )
            db.session.add(template)
            created += 1

        db.session.commit()

        print(f"Inserted {created} default templates")
        print(f"Egyptian courts loaded in static meta service: {len(get_egyptian_courts())}")


if __name__ == "__main__":
    run_seed()
