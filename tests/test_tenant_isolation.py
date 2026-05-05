from app.extensions import db
from app.models import Client
from app.models.enums import UserRole


def test_office_cannot_access_other_office_client(client, make_user, auth_headers):
    office_a, owner_a = make_user("oa@example.com", role=UserRole.OWNER, office_name="Office A")
    office_b, owner_b = make_user("ob@example.com", role=UserRole.OWNER, office_name="Office B")

    create = client.post(
        "/api/v1/clients/",
        headers=auth_headers(owner_a),
        json={
            "client_type": "individual",
            "full_name_ar": "عميل أ",
            "national_id_or_commercial_reg": "A-1",
            "primary_phone": "0100000",
        },
    )
    assert create.status_code == 201
    client_id = create.json["data"]["id"]

    get_other = client.get(f"/api/v1/clients/{client_id}", headers=auth_headers(owner_b))
    assert get_other.status_code in {403, 404}
