from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)
    article_context: list[dict[str, Any]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
