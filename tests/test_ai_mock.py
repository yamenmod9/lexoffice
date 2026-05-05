from unittest.mock import Mock

from app.models import Document
from app.models.enums import EntityType, GlobalDocumentType, UserRole


def test_ai_summary_endpoint_mocks_celery(client, make_user, auth_headers, monkeypatch, db_session):
    _, owner = make_user("ai-owner@example.com", role=UserRole.OWNER)

    doc = Document(
        office_id=owner.office_id,
        entity_type=EntityType.CLIENT,
        entity_id=owner.id,
        doc_type=GlobalDocumentType.OTHER,
        file_name="a.pdf",
        file_url="/tmp/a.pdf",
        file_size=1,
        mime_type="application/pdf",
        uploaded_by=owner.id,
    )
    db_session.add(doc)
    db_session.commit()

    mocked = Mock()
    mocked.id = "task-123"

    from app.api import ai as ai_module

    monkeypatch.setattr(ai_module.summarize_document_task, "delay", lambda *_args, **_kwargs: mocked)

    response = client.post("/api/v1/ai/summarize", headers=auth_headers(owner), json={"document_id": str(doc.id)})
    assert response.status_code == 202
    assert response.json["data"]["task_id"] == "task-123"
