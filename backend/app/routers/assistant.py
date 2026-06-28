from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.assistant import SUGGESTED_QUESTIONS
from app.agentic.conversational import ConversationalAgent, assistant_status
from app.db import get_db

router = APIRouter(tags=["assistant"])

_agent = ConversationalAgent()


class ChatMessage(BaseModel):
    role: str
    content: str


class AssistantChatRequest(BaseModel):
    messages: list[ChatMessage]
    week: str | None = None
    correlation_id: str | None = None


class AssistantReference(BaseModel):
    cluster_id: str
    site_id: str = ""
    site_name: str = ""
    theme: str = ""
    week: str = ""
    label: str


class AssistantChatResponse(BaseModel):
    answer: str
    references: list[AssistantReference] = Field(default_factory=list)
    a2a_correlation_id: str
    tools_used: list[str] = Field(default_factory=list)
    agentic_rounds: int = 1
    mode: str = "offline"


@router.get("/assistant/status")
def status():
    return assistant_status()


@router.get("/assistant/suggestions")
def suggestions():
    return {"questions": SUGGESTED_QUESTIONS}


@router.post("/assistant/chat", response_model=AssistantChatResponse)
def assistant_chat(body: AssistantChatRequest, db: Session = Depends(get_db)):
    msgs = [{"role": m.role, "content": m.content} for m in body.messages]
    question = msgs[-1]["content"] if msgs else ""
    result = _agent.run(db, question, week=body.week, history=msgs[:-1])
    db.commit()
    refs = [AssistantReference(**r) for r in result["references"] if r.get("cluster_id")]
    return AssistantChatResponse(
        answer=result["answer"],
        references=refs,
        a2a_correlation_id=result["a2a_correlation_id"],
        tools_used=result.get("tools_used", []),
        agentic_rounds=result.get("agentic_rounds", 1),
        mode=result.get("mode", "offline"),
    )


@router.post("/assistant/chat/stream")
def assistant_chat_stream(body: AssistantChatRequest, db: Session = Depends(get_db)):
    """SSE stream — real OpenAI tokens when AI mode is enabled."""
    msgs = [{"role": m.role, "content": m.content} for m in body.messages]
    question = msgs[-1]["content"] if msgs else ""

    def gen():
        for event in _agent.stream(db, question, week=body.week, history=msgs[:-1]):
            yield f"data: {json.dumps(event)}\n\n"
        db.commit()

    return StreamingResponse(gen(), media_type="text/event-stream")
