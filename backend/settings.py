from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _csv(value: str, default: str) -> tuple[str, ...]:
    raw = value or default
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")
    llm_api_mode: str = os.getenv("LLM_API_MODE", os.getenv("API_MODE", "aicredits"))
    llm_api_key: str = os.getenv("LLM_API_KEY") or os.getenv("AI_CREDITS_KEY", "")
    openai_direct_key: str = os.getenv("OPENAI_DIRECT_KEY", "")
    llm_base_url: str = os.getenv(
        "LLM_BASE_URL",
        os.getenv("AI_CREDITS_BASE_URL", "https://api.aicredits.in/v1"),
    )
    chat_shared_secret: str = os.getenv("CHAT_SHARED_SECRET", "")
    ip_hash_salt: str = os.getenv("IP_HASH_SALT", "")
    firebase_sa_b64: str = os.getenv("FIREBASE_SA_B64", "")
    firebase_database_url: str = os.getenv(
        "FIREBASE_DATABASE_URL",
        "https://meridian-pulse-94152-default-rtdb.firebaseio.com",
    )
    firebase_database_emulator_host: str = os.getenv(
        "FIREBASE_DATABASE_EMULATOR_HOST", ""
    )
    firebase_web_config: str = os.getenv("VITE_FIREBASE_WEB_CONFIG", "")
    cors_origins: tuple[str, ...] = _csv(
        os.getenv("CORS_ORIGINS", ""),
        "http://localhost:5173",
    )
    chat_per_minute: int = int(os.getenv("CHAT_PER_MINUTE", "10"))
    chat_per_day: int = int(os.getenv("CHAT_PER_DAY", "100"))
    daily_token_budget: int = int(os.getenv("DAILY_TOKEN_BUDGET", "5000"))
    max_history: int = 6
    max_articles: int = 20
    max_upload_bytes: int = 10 * 1024 * 1024
    max_pdf_pages: int = 100


settings = Settings()
