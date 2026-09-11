"""Firebase Realtime Database access.

The module name is retained so existing ingestion imports remain stable.
"""

from __future__ import annotations

import base64
import json
from typing import Any

import firebase_admin
from firebase_admin import credentials, db

from .settings import settings


PUBLIC_PATHS = {"articles", "sec_filings", "transcripts", "meta"}
SERVER_PATHS = {"seen", "seen_title", "usage"}


def get_db():
    if not settings.firebase_sa_b64 and not settings.firebase_database_emulator_host:
        raise RuntimeError("FIREBASE_SA_B64 is not configured.")
    if not settings.firebase_database_url:
        raise RuntimeError("FIREBASE_DATABASE_URL is not configured.")

    try:
        firebase_admin.get_app()
    except ValueError:
        if settings.firebase_database_emulator_host:
            firebase_admin.initialize_app(
                options={"databaseURL": settings.firebase_database_url}
            )
        else:
            service_account = json.loads(
                base64.b64decode(settings.firebase_sa_b64).decode("utf-8")
            )
            firebase_admin.initialize_app(
                credentials.Certificate(service_account),
                {"databaseURL": settings.firebase_database_url},
            )
    return db.reference("/")


def public_collection(name: str):
    if name not in PUBLIC_PATHS:
        raise ValueError(f"Path is not public: {name}")
    return get_db().child(name)


def server_collection(name: str):
    if name not in SERVER_PATHS:
        raise ValueError(f"Path is not server-only: {name}")
    return get_db().child(name)


def set_document(collection: str, document_id: str, data: dict[str, Any]) -> None:
    if collection not in PUBLIC_PATHS | SERVER_PATHS:
        raise ValueError(f"Unknown Firebase path: {collection}")
    get_db().child(collection).child(document_id).update(data)
