from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from .firestore import server_collection
from .models import ChatRequest, ChatResponse, HealthResponse
from .services.chat import answer_chat
from .services.transcripts import analyze_transcript
from .settings import settings

TRANSCRIPT_DIR = Path(__file__).resolve().parents[1] / "assets" / "data"


def _client_key(request: Request) -> str:
    address = get_remote_address(request)
    return hashlib.sha256(
        f"{address}{settings.ip_hash_salt}".encode("utf-8")
    ).hexdigest()


limiter = Limiter(key_func=_client_key, default_limits=[])
app = FastAPI(title="Meridian Pulse API", version="1.0.0")
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Chat rate limit exceeded."})


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Chat-Secret"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "connect-src 'self' https://meridian-pulse-94152-default-rtdb.firebaseio.com "
        "https://*.onrender.com http://localhost:8000 http://localhost:9000; "
        "script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; frame-ancestors 'none'"
    )
    return response


def _reserve_daily_tokens(tokens: int) -> None:
    day = datetime.now(timezone.utc).date().isoformat()
    reference = server_collection("usage").child(day)

    def update(current):
        current = current or {"tokens": 0, "chat_requests": 0, "budget_hits": 0}
        if current.get("tokens", 0) + tokens > settings.daily_token_budget:
            current["budget_hits"] = current.get("budget_hits", 0) + 1
            raise RuntimeError("Daily token budget exceeded.")
        current["tokens"] = current.get("tokens", 0) + tokens
        current["chat_requests"] = current.get("chat_requests", 0) + 1
        return current

    try:
        reference.transaction(update)
    except RuntimeError as error:
        if str(error) == "Daily token budget exceeded.":
            raise HTTPException(status_code=429, detail=str(error)) from error
        raise


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "Meridian Pulse API",
        "status": "ok",
        "health": "/health",
        "docs": "/docs",
    }


@app.post("/chat", response_model=ChatResponse)
@limiter.limit(f"{settings.chat_per_day}/day")
@limiter.limit(f"{settings.chat_per_minute}/minute")
def chat(
    payload: ChatRequest,
    request: Request,
    x_chat_secret: str | None = Header(default=None),
) -> ChatResponse:
    if settings.chat_shared_secret and x_chat_secret != settings.chat_shared_secret:
        raise HTTPException(status_code=401, detail="Invalid chat credentials.")
    prompt_size = len(payload.query) + sum(len(message.content) for message in payload.history)
    estimated_tokens = max(1, prompt_size // 4)
    _reserve_daily_tokens(estimated_tokens)
    try:
        response, actual_tokens = answer_chat(
            payload.query,
            [message.model_dump() for message in payload.history[-settings.max_history:]],
            payload.article_context[:settings.max_articles],
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        error_text = str(error).lower()
        if "insufficient" in error_text or "quota" in error_text or "balance" in error_text:
            raise HTTPException(
                status_code=503,
                detail="The AI provider has insufficient credits. Add provider credits and try again.",
            ) from error
        raise HTTPException(status_code=502, detail="Chat provider unavailable.") from error
    if actual_tokens > estimated_tokens:
        _reserve_daily_tokens(actual_tokens - estimated_tokens)
    return ChatResponse(response=response)


@app.post("/transcripts/analyze")
async def transcript_analyze(upload: UploadFile = File(...)) -> dict:
    content = await upload.read(settings.max_upload_bytes + 1)
    try:
        return analyze_transcript(upload.filename or "transcript.txt", content)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail="Transcript analysis provider unavailable.") from error


@app.get("/transcripts/bundled")
def bundled_transcripts() -> list[str]:
    if not TRANSCRIPT_DIR.is_dir():
        return []
    return sorted(
        path.name for path in TRANSCRIPT_DIR.glob("*.txt") if path.is_file()
    )


@app.get("/transcripts/bundled/{filename}")
def bundled_transcript(filename: str) -> FileResponse:
    safe_name = os.path.basename(filename)
    path = TRANSCRIPT_DIR / safe_name
    if path.suffix.lower() != ".txt" or not path.is_file():
        raise HTTPException(status_code=404, detail="Transcript not found.")
    return FileResponse(path, media_type="text/plain", filename=safe_name)
