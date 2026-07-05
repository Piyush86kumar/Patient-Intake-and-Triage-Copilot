from fastapi.testclient import TestClient

from triage_copilot.api.main import app
from triage_copilot.controller.state_machine import ControllerResponse


client = TestClient(app)


def test_create_conversation_returns_conversation_id():
    response = client.post(
        "/conversations",
        headers={"X-API-Key": "changeme_local_dev_key"},
    )

    assert response.status_code == 200
    assert "conversation_id" in response.json()


def test_state_endpoint_returns_patient_case():
    create_response = client.post(
        "/conversations",
        headers={"X-API-Key": "changeme_local_dev_key"},
    )
    conversation_id = create_response.json()["conversation_id"]

    response = client.get(
        f"/conversations/{conversation_id}/state",
        headers={"X-API-Key": "changeme_local_dev_key"},
    )

    assert response.status_code == 200
    assert response.json()["conversation_id"] == conversation_id


def test_messages_requires_api_key():
    response = client.post(
        "/conversations/example/messages",
        json={"message": "I have chest pain"},
    )

    assert response.status_code == 401


def test_messages_calls_process_turn(monkeypatch):
    async def fake_process_turn(conversation_id: str, message: str) -> ControllerResponse:
        return ControllerResponse(message="handled", status="GATHERING")

    monkeypatch.setattr("triage_copilot.api.main.process_turn", fake_process_turn)

    response = client.post(
        "/conversations/example/messages",
        json={"message": "I have chest pain"},
        headers={"X-API-Key": "changeme_local_dev_key"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "handled"
