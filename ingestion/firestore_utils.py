from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    parts = urlsplit((url or "").strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith(("utm_", "fbclid", "gclid"))
    ]
    host = (parts.hostname or "").lower()
    netloc = host
    if parts.port and parts.port not in (80, 443):
        netloc = f"{host}:{parts.port}"
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), netloc, path, urlencode(query), ""))


def url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()


def title_hash(title: str) -> str:
    words = re.findall(r"[a-z0-9]+", (title or "").lower())
    return hashlib.sha256(" ".join(words).encode("utf-8")).hexdigest()


def parse_utc_date(value: object, fallback: datetime | None = None) -> datetime:
    fallback = fallback or datetime.now(timezone.utc)
    if isinstance(value, datetime):
        parsed = value
    elif value:
        text = str(value).strip()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(text)
            except (TypeError, ValueError, IndexError):
                return fallback
    else:
        return fallback
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def excerpt(text: str, limit: int = 300) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:limit]
