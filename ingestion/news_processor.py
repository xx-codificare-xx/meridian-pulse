from __future__ import annotations

from datetime import datetime, timedelta, timezone

from engine.tag_scorer import score_all_articles
from ingestion.firestore_utils import canonical_title, parse_utc_date, title_hash, url_hash
from ingestion.rss_fetcher import fetch_all_rss
from ingestion.sec_fetcher import fetch_all_sec, summarize_filing


def _firebase_state():
    from backend.firestore import get_db, server_collection

    return get_db(), server_collection


def fetch_all_news(selected_tags: list | None = None, progress_callback=None) -> list:
    """Fetch, deduplicate, score, and upsert the current ingestion batch."""
    started_at = datetime.now(timezone.utc)
    db, server_collection = _firebase_state()
    rss_articles = fetch_all_rss()
    sec_filings = fetch_all_sec()
    candidates = []
    skipped = 0
    batch_urls = set()
    batch_titles = set()

    for article in rss_articles + sec_filings:
        key = (
            article.get("id")
            if article.get("type") == "sec_filing"
            else url_hash(article["url"])
        )
        title_key = title_hash(canonical_title(article.get("title", "")))
        if key in batch_urls or title_key in batch_titles:
            skipped += 1
            continue

        seen_url = server_collection("seen").child(key).get() or {}
        seen_title = server_collection("seen_title").child(title_key).get()
        if seen_url.get("suppressed") or seen_title is not None:
            skipped += 1
            continue

        article["_document_id"] = key
        article["_title_hash"] = title_key
        if article.get("type") == "sec_filing":
            article = summarize_filing(article)
        batch_urls.add(key)
        batch_titles.add(title_key)
        candidates.append(article)

    scored = score_all_articles(
        candidates,
        selected_tags or [],
        progress_callback=progress_callback,
    )

    for article in scored:
        article_id = article.pop("_document_id")
        title_id = article.pop("_title_hash")
        article["ingested_at"] = article.get("ingested_at", started_at)
        article["published_at"] = article.get("published_at", started_at)
        collection = "sec_filings" if article.get("type") == "sec_filing" else "articles"
        db.child(collection).child(article_id).update(_firebase_data(article))
        server_collection("seen").child(article_id).update(
            {
                "seen_at": started_at.isoformat(),
                "suppressed": False,
                "type": article.get("type"),
            }
        )
        server_collection("seen_title").child(title_id).update(
            {"seen_at": started_at.isoformat()}
        )

    db.child("meta").child("last_run").update(
        {
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "items_fetched": len(rss_articles) + len(sec_filings),
            "items_new": len(candidates),
            "items_scored": len(scored),
            "items_suppressed": skipped,
        }
    )
    _retention_sweep(db, server_collection)
    return scored


def _retention_sweep(db, server_collection) -> None:
    now = datetime.now(timezone.utc)
    article_cutoff = now - timedelta(days=14)
    seen_cutoff = now - timedelta(days=90)

    for collection in ("articles", "sec_filings"):
        records = db.child(collection).get() or {}
        for key, record in records.items():
            if parse_utc_date(record.get("ingested_at")) < article_cutoff:
                db.child(collection).child(key).delete()

    records = server_collection("seen").get() or {}
    for key, record in records.items():
        if (
            not record.get("suppressed", False)
            and parse_utc_date(record.get("seen_at")) < seen_cutoff
        ):
            server_collection("seen").child(key).delete()


def _firebase_data(data: dict) -> dict:
    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in data.items()
    }


if __name__ == "__main__":
    fetch_all_news()
