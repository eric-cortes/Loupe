from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents.orchestrator import run_conversation

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Archive Curator Chat")


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class Match(BaseModel):
    id: int
    file_path: str
    caption: str | None
    camera_model: str | None
    capture_time: str | None
    rating: int | None
    similarity: float | None
    keywords: list[str]
    collections: list[str]


class ChatResponse(BaseModel):
    answer: str
    structured_calls: list[dict]
    matches: list[Match]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    result = run_conversation([m.model_dump() for m in req.messages])
    return ChatResponse(**result)


# Registered last so /health and /chat above take precedence; serves the
# Vite-built frontend (frontend/ -> pnpm build -> here) with SPA index fallback.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
