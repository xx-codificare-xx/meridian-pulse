import os
import sys
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TAGS, HIGH_PRIORITY_THRESHOLD, MIN_URGENCY_THRESHOLD
from engine.llm_handler import get_llm, ask_llm
from engine.prompts import TAG_SCORING_PROMPT

SCORING_PROMPT = TAG_SCORING_PROMPT

# SCORING_PROMPT = """You are a senior healthcare strategy analyst at BCBS (Blue Cross Blue Shield).

# Analyze this article and determine which tags apply based on these definitions:

# - Time Sensitivity: Requires immediate action or decision within days/weeks
# - Strategic Alignment: Directly impacts BSC's long-term strategy or market position  
# - Regulatory Risk: Involves CMS, HHS, ACA, or government policy changes
# - Competitive Momentum: Involves competitor moves, market shifts, or industry trends
# - Financial Impact: Affects premiums, MLR, costs, or financial performance
# - Member Impact: Directly affects member benefits, access, or experience

# For each tag return true or false.
# Also return a confidence score 0.0 to 1.0 for your overall assessment.
# Also return one sentence of reasoning.

# Return ONLY valid JSON. No markdown. No explanation outside JSON.

# Article Title: {title}
# Article Summary: {summary}

# Return exactly this format:
# {{
#     "Time Sensitivity": true or false,
#     "Strategic Alignment": true or false,
#     "Regulatory Risk": true or false,
#     "Competitive Momentum": true or false,
#     "Financial Impact": true or false,
#     "Member Impact": true or false,
#     "confidence": 0.0 to 1.0,
#     "reasoning": "one sentence"
# }}"""


def score_article(article: dict, selected_tags: list, llm=None) -> dict:
    """Score a single article against selected tags."""
    if llm is None:
        llm = get_llm(role="scorer")

    prompt = SCORING_PROMPT.format(
        title=article.get("title", ""),
        summary=article.get("summary", "")[:600],
    )

    try:
        raw = ask_llm(prompt, llm)
        # Strip markdown fences if present
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
    except Exception as e:
        print(f"[Scorer] Error on '{article.get('title', '')}': {e}")
        result = {tag: False for tag in TAGS}
        result["confidence"] = 0.0
        result["reasoning"] = "Scoring failed"

    # Calculate urgency score — only for user selected tags
    matched = []
    score = 0.0
    for tag in selected_tags:
        if result.get(tag, False):
            matched.append(tag)
            score += TAGS.get(tag, 0.0)

    # Cap at 1.0
    score = min(score, 1.0)

    # Urgency label
    if score >= HIGH_PRIORITY_THRESHOLD:
        label = "🔴 High"
    elif score >= 0.20:
        label = "🟡 Medium"
    elif score >= MIN_URGENCY_THRESHOLD:
        label = "🟢 Low"
    else:
        label = "🔵 Minimal"
        
    article["tags_matched"]  = matched
    article["urgency_score"] = round(score, 2)
    article["urgency_label"] = label
    article["confidence"]    = result.get("confidence", 0.0)
    article["reasoning"]     = result.get("reasoning", "")

    return article


def score_all_articles(
    articles: list,
    selected_tags: list,
    progress_callback=None
) -> list:
    """Score all articles, filter irrelevant, sort by urgency."""
    from engine.llm_handler import is_healthcare_relevant

    llm_filter = get_llm(role="prefilter")
    llm_scorer = get_llm(role="scorer")

    scored    = []
    filtered  = 0
    total     = len(articles)

    for i, article in enumerate(articles):
        print(f"[Pipeline] Processing {i+1}/{total}: {article['title'][:60]}")
        
        # Layer 1 — pre-filter
        if not is_healthcare_relevant(article, llm_filter):
            filtered += 1
            if progress_callback:
                progress_callback(i + 1, total)
            continue

        # Layer 2 — full tag scoring
        article = score_article(article, selected_tags, llm_scorer)

        if article["urgency_score"] >= MIN_URGENCY_THRESHOLD:
            scored.append(article)

        if progress_callback:
            progress_callback(i + 1, total)

    print(f"[Scorer] {filtered} filtered out, {len(scored)} scored and relevant")
    scored.sort(key=lambda x: x["urgency_score"], reverse=True)
    return scored
    


if __name__ == "__main__":
    test_article = {
        "title":   "CMS proposes new Medicare Advantage payment rules for 2026",
        "summary": "The Centers for Medicare & Medicaid Services released proposed "
                   "payment rules that could significantly impact Medicare Advantage "
                   "plans, with potential rate cuts affecting major insurers.",
        "source":  "STAT News",
        "url":     "https://statnews.com/test",
        "published": "2026-05-20",
    }

    selected = ["Time Sensitivity", "Regulatory Risk", "Financial Impact"]
    result = score_article(test_article, selected)

    print(f"\nTitle:      {result['title']}")
    print(f"Score:      {result['urgency_score']}")
    print(f"Label:      {result['urgency_label']}")
    print(f"Tags:       {result['tags_matched']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Reasoning:  {result['reasoning']}")