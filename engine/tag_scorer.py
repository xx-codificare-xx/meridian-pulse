import os
import sys
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TAGS
from engine.prompts import TAG_SCORING_PROMPT

BATCH_SIZE    = 10   # articles per pre-filter call
MAX_WORKERS   = 5    # parallel scoring threads
PREFILTER_FALLBACK_LIMIT = 20


def get_llm_client(role="scorer"):
    from engine.llm_handler import get_llm
    return get_llm(role=role)


class _ProviderFallback:
    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback

    def invoke(self, messages):
        try:
            return self.primary.invoke(messages)
        except Exception as error:
            text = str(error).lower()
            if not any(
                marker in text
                for marker in (
                    "balance_insufficient",
                    "insufficient_quota",
                    "insufficient balance",
                    "error code: 402",
                )
            ):
                raise
            return self.fallback.invoke(messages)


def get_resilient_llm_client(role="scorer"):
    from langchain_openai import ChatOpenAI
    from engine.llm_handler import get_llm
    from config import AI_CREDITS_BASE_URL
    primary = get_llm(role=role)
    fallback = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=os.getenv("LLM_API_KEY") or os.getenv("AI_CREDITS_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL", AI_CREDITS_BASE_URL),
        max_tokens=512,
    )
    return _ProviderFallback(primary, fallback)


def batch_prefilter(articles: list, llm=None) -> list:
    """
    Send BATCH_SIZE articles in one API call.
    Returns list of booleans — True = relevant.
    """
    if llm is None:
        llm = get_llm_client("prefilter")

    lines = []
    for i, a in enumerate(articles, 1):
        title   = a.get("title", "")[:120]
        summary = a.get("summary", "")[:200]
        lines.append(f"{i}. Title: {title}\n   Summary: {summary}")

    prompt = f"""You are a filter for a US health insurance company (BCBS).

For each article below, reply YES or NO if it is relevant to:
- Health insurance, payers, or managed care
- Medicare, Medicaid, or ACA
- Healthcare policy or regulation
- Competitor insurers (UnitedHealth, Elevance, CVS, Humana, Cigna)
- Healthcare costs, claims, or benefits
- Women in healthcare

Articles:
{chr(10).join(lines)}

Reply ONLY in this exact format with no other text:
1:YES 2:NO 3:YES 4:YES 5:NO 6:YES 7:NO 8:YES 9:NO 10:YES"""

    try:
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        raw      = response.content.strip()

        # Parse "1:YES 2:NO 3:YES ..."
        results  = {}
        for token in raw.split():
            if ":" in token:
                idx, verdict = token.split(":", 1)
                try:
                    results[int(idx)] = verdict.strip().upper() == "YES"
                except ValueError:
                    pass

        return [results.get(i, True) for i in range(1, len(articles) + 1)]

    except Exception as e:
        print(f"[Batch Filter] Error: {e}")
        raise RuntimeError("Prefilter unavailable") from e


def score_single(article: dict, selected_tags: list, llm=None) -> dict:
    """Evaluate all tags; urgency is calculated by the client."""
    if llm is None:
        llm = get_resilient_llm_client("scorer")

    prompt = TAG_SCORING_PROMPT.format(
        title   = article.get("title", ""),
        summary = article.get("summary", "")[:600],
    )

    try:
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        raw      = response.content.strip()
        raw      = raw.replace("```json", "").replace("```", "").strip()
        result   = json.loads(raw)
    except Exception as e:
        print(f"[Scorer] Error on '{article.get('title','')[:50]}': {e}")
        result = {tag: False for tag in TAGS}
        result["confidence"] = 0.0
        result["reasoning"]  = "Scoring failed"
        article["scored"] = False

    article["tags_evaluated"] = {
        tag: bool(result.get(tag, False)) for tag in TAGS
    }
    article["tags_matched"] = [
        tag for tag, matched in article["tags_evaluated"].items() if matched
    ]
    article["confidence"]    = result.get("confidence", 0.0)
    article["reasoning"]     = result.get("reasoning", "")
    article.setdefault("scored", True)
    return article


def score_all_articles(
    articles: list,
    selected_tags: list,
    progress_callback=None
) -> list:
    """
    Full pipeline:
    1. Batch pre-filter (BATCH_SIZE articles per LLM call)
    2. Parallel tag scoring (MAX_WORKERS threads)
    """
    total      = len(articles)
    processed  = 0

    # ── Step 1: Batch pre-filter ──────────────────────────────────
    print(f"[Scorer] Pre-filtering {total} articles in batches of {BATCH_SIZE}...")
    llm_filter  = get_resilient_llm_client("prefilter")
    relevant    = []
    filtered_out = 0

    for i in range(0, total, BATCH_SIZE):
        batch   = articles[i:i + BATCH_SIZE]
        try:
            results = batch_prefilter(batch, llm_filter)
        except Exception as exc:
            print(f"[Scorer] Prefilter failed: {exc}")
            results = [None] * len(batch)

        for article, is_relevant in zip(batch, results):
            if is_relevant is None:
                article["scored"] = False
                if len(relevant) < PREFILTER_FALLBACK_LIMIT:
                    relevant.append(article)
            elif is_relevant:
                relevant.append(article)
            else:
                filtered_out += 1

        processed += len(batch)
        if progress_callback:
            progress_callback(processed // 2, total)

        relevant_count = sum(result is True for result in results)
        fallback_count = sum(result is None for result in results)
        print(f"[Scorer] Batch {i//BATCH_SIZE + 1} done "
              f"— {relevant_count}/{len(batch)} relevant"
              f"{f' ({fallback_count} fallback)' if fallback_count else ''}")

    print(f"[Scorer] Pre-filter done: {filtered_out} removed, "
          f"{len(relevant)} remaining")

    # ── Step 2: Parallel tag scoring ─────────────────────────────
    print(f"[Scorer] Scoring {len(relevant)} articles "
          f"with {MAX_WORKERS} parallel workers...")

    scored    = []
    score_idx = [0]

    def score_and_track(article):
        llm    = get_resilient_llm_client("scorer")
        result = score_single(article, selected_tags, llm)
        score_idx[0] += 1
        if progress_callback:
            progress_callback(
                total // 2 + score_idx[0],
                total
            )
        return result

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(score_and_track, a): a
            for a in relevant
        }
        for future in as_completed(futures):
            try:
                result = future.result()
                scored.append(result)
            except Exception as e:
                print(f"[Scorer] Thread error: {e}")

    scored.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)
    print(f"[Scorer] Done — {len(scored)} articles scored")
    return scored


if __name__ == "__main__":
    test_articles = [
        {
            "title":   "CMS proposes new Medicare Advantage payment rules",
            "summary": "Federal regulators released proposed payment rules "
                       "affecting Medicare Advantage plans significantly.",
        },
        {
            "title":   "Lakers win NBA championship",
            "summary": "Los Angeles Lakers defeated Boston Celtics in game 7.",
        },
        {
            "title":   "Medicaid expansion faces new federal limits",
            "summary": "Federal government announces new restrictions on "
                       "Medicaid expansion funding for states.",
        },
    ]
    selected = ["Time Sensitivity", "Regulatory Risk", "Financial Impact"]
    results  = score_all_articles(test_articles, selected)
    for r in results:
        print(f"\n{r['urgency_label']} | {r['urgency_score']} | {r['title'][:60]}")
        print(f"  Tags: {r['tags_matched']}")