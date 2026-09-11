from __future__ import annotations

from engine.prompts import CHATBOT_PROMPT

from ..llm import ask_llm_with_usage
from ..settings import settings


def answer_chat(
    query: str,
    history: list[dict[str, str]],
    article_context: list[dict],
) -> tuple[str, int]:
    if not query.strip():
        raise ValueError("Query must not be empty.")

    bounded_history = history[-settings.max_history:]
    bounded_articles = article_context[:settings.max_articles]
    context = "\n".join(
        f"- [{article.get('urgency_label', '')}] {article.get('title', '')} "
        f"({article.get('source', '')}, {article.get('published', '')}): "
        f"{article.get('reasoning', '')}"
        for article in bounded_articles
    ) or "No articles fetched yet."
    formatted_history = "\n".join(
        f"{message['role'].upper()}: {message['content']}"
        for message in bounded_history
    )

    return ask_llm_with_usage(
        CHATBOT_PROMPT.format(
            context=context,
            history=formatted_history,
            query=query.strip(),
        )
    )
