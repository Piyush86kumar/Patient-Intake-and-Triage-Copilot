from __future__ import annotations

import uuid

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel

import gradio as gr

from triage_copilot.config import settings
from triage_copilot.controller.patient_case import PatientCase
from triage_copilot.controller.state_machine import process_turn
from ui.gradio_app import demo as gradio_demo


app = FastAPI(title="Triage Copilot API")
app = gr.mount_gradio_app(app, gradio_demo, path="/ui")


class MessageRequest(BaseModel):
    message: str


class ConversationCreateResponse(BaseModel):
    conversation_id: str


class MessageResponse(BaseModel):
    message: str
    status: str


class PatientCaseResponse(BaseModel):
    conversation_id: str
    facts: dict
    matched_protocol_id: str | None = None
    questions_asked: list[str] = []
    disposition: str | None = None
    status: str
    turn_count: int


def _require_api_key(x_api_key: str | None) -> None:
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@app.post("/conversations", response_model=ConversationCreateResponse)
def create_conversation(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> ConversationCreateResponse:
    _require_api_key(x_api_key)
    conversation_id = str(uuid.uuid4())
    case = PatientCase.new(conversation_id)
    case.save()
    return ConversationCreateResponse(conversation_id=conversation_id)


@app.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def post_message(
    conversation_id: str,
    request: MessageRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> MessageResponse:
    _require_api_key(x_api_key)
    response = await process_turn(conversation_id, request.message)
    return MessageResponse(message=response.message, status=response.status)


@app.get("/conversations/{conversation_id}/state", response_model=PatientCaseResponse)
def get_state(conversation_id: str, x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> PatientCaseResponse:
    _require_api_key(x_api_key)
    case = PatientCase.load(conversation_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return PatientCaseResponse(
        conversation_id=case.conversation_id,
        facts=case.facts.model_dump(),
        matched_protocol_id=case.matched_protocol_id,
        questions_asked=case.questions_asked,
        disposition=case.disposition,
        status=case.status.value,
        turn_count=case.turn_count,
    )


__all__ = ["app"]
