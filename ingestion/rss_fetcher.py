# import feedparser
# import time
# import sys
# import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from config import RSS_FEEDS, MAX_ARTICLES_PER_SOURCE, SEC_RATE_LIMIT_SLEEP


# def parse_date(entry):
#     from datetime import datetime, timezone
#     for field in ["published_parsed", "updated_parsed"]:
#         val = getattr(entry, field, None)
#         if val:
#             try:
#                 return datetime(*val[:6], tzinfo=timezone.utc).strftime("%Y-%m-%d")
#             except:
#                 pass
#     return datetime.now().strftime("%Y-%m-%d")


# def fetch_feed(name, url):
#     articles = []
#     try:
#         feed = feedparser.parse(url)
#         for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
#             articles.append({
#                 "id":            entry.get("id", entry.get("link", "")),
#                 "title":         entry.get("title", "").strip(),
#                 "summary":       entry.get("summary", entry.get("description", "")).strip(),
#                 "url":           entry.get("link", ""),
#                 "source":        name,
#                 "published":     parse_date(entry),
#                 "type":          "rss",
#                 "tags_matched":  [],
#                 "urgency_score": 0.0,
#                 "urgency_label": "Unscored",
#             })
#     except Exception as e:
#         print(f"[RSS] Failed {name}: {e}")
#     return articles


# def fetch_all_rss():
#     all_articles = []
#     seen = set()

#     for name, url in RSS_FEEDS.items():
#         print(f"[RSS] Fetching: {name}")
#         articles = fetch_feed(name, url)
#         for a in articles:
#             if a["url"] not in seen:
#                 seen.add(a["url"])
#                 all_articles.append(a)
#         print(f"      → {len(articles)} articles")
#         time.sleep(SEC_RATE_LIMIT_SLEEP)

#     print(f"\n[RSS] Total unique articles: {len(all_articles)}")
#     return all_articles


# if __name__ == "__main__":
#     articles = fetch_all_rss()
#     for a in articles[:3]:
#         print(f"\n{a['source']} | {a['published']}")
#         print(f"  {a['title']}")
#         print(f"  {a['url']}")

import feedparser # type: ignore
import time
import sys
import os
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RSS_FEEDS, MAX_ARTICLES_PER_SOURCE, SEC_RATE_LIMIT_SLEEP
from ingestion.firestore_utils import excerpt, parse_utc_date


def clean_text(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text).strip()

def parse_date(entry):
    from datetime import datetime, timezone
    for field in ["published_parsed", "updated_parsed"]:
        val = getattr(entry, field, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc).strftime("%Y-%m-%d")
            except:
                pass
    return datetime.now().strftime("%Y-%m-%d")


def fetch_feed(name, url):
    articles = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
            ingested_at = parse_utc_date(None)
            published_at = parse_utc_date(
                entry.get("published") or entry.get("updated"),
                ingested_at,
            )
            url = entry.get("link", "").strip()
            if not url:
                continue
            articles.append({
                "id":            entry.get("id", entry.get("link", "")),
                # "title":         entry.get("title", "").strip(),
                # "summary":       entry.get("summary", entry.get("description", "")).strip(),
                "title":   clean_text(entry.get("title", "")),
                "summary": excerpt(clean_text(entry.get("summary", entry.get("description", "")))),
                "url":           url,
                "source":        name,
                "published":     published_at.date().isoformat(),
                "published_at":  published_at,
                "ingested_at":   ingested_at,
                "type":          "rss",
                "tags_matched":  [],
                "urgency_score": 0.0,
                "urgency_label": "Unscored",
            })
    except Exception as e:
        print(f"[RSS] Failed {name}: {e}")
    return articles


def fetch_all_rss():
    all_articles = []
    seen = set()

    for name, url in RSS_FEEDS.items():
        print(f"[RSS] Fetching: {name}")
        articles = fetch_feed(name, url)
        for a in articles:
            if a["url"] not in seen:
                seen.add(a["url"])
                all_articles.append(a)
        print(f"      → {len(articles)} articles")
        time.sleep(SEC_RATE_LIMIT_SLEEP)

    print(f"\n[RSS] Total unique articles: {len(all_articles)}")
    return all_articles


if __name__ == "__main__":
    articles = fetch_all_rss()
    for a in articles[:5]:
        print(f"\n{a['source']} | {a['published']}")
        print(f"  {a['title']}")
        print(f"  {a['url']}")