from __future__ import annotations

from config import LLM_MODELS

from .settings import settings


def get_llm(role: str = "scorer", max_tokens: int = 512):
    from langchain_openai import ChatOpenAI
    from config import LLM_MODEL_PREFILTER, LLM_MODEL_SCORER

    if role not in LLM_MODELS.get(settings.llm_provider, {}):
        raise ValueError(f"Unknown LLM role: {role}")

    if settings.llm_api_mode == "openai_direct":
        api_key = settings.openai_direct_key
        model = LLM_MODELS["openai"][role]
        base_url = None
    else:
        api_key = settings.llm_api_key
        model = {
            "prefilter": LLM_MODEL_PREFILTER,
            "scorer": LLM_MODEL_SCORER,
        }.get(role)
        if not model:
            raise ValueError(f"Unknown LLM role: {role}")
        base_url = settings.llm_base_url

    if not api_key:
        raise RuntimeError("LLM credentials are not configured.")

    kwargs = {
        "model": model,
        "api_key": api_key,
        "max_tokens": max_tokens,
    }
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def ask_llm(prompt: str, role: str = "scorer", max_tokens: int = 512) -> str:
    response, _ = ask_llm_with_usage(prompt, role, max_tokens)
    return response


def ask_llm_with_usage(
    prompt: str, role: str = "scorer", max_tokens: int = 512
) -> tuple[str, int]:
    from langchain_core.messages import HumanMessage

    message = HumanMessage(content=prompt)
    client = get_llm(role, max_tokens=max_tokens)
    try:
        response = client.invoke([message])
    except Exception as error:
        if (
            settings.llm_api_mode not in {"aicredits", "ai_credits"}
            or not _is_provider_credit_error(error)
            or role not in {"prefilter", "scorer"}
        ):
            raise
        from langchain_openai import ChatOpenAI
        fallback = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            max_tokens=max_tokens,
        )
        response = fallback.invoke([message])
    usage = getattr(response, "usage_metadata", {}) or {}
    tokens = usage.get("total_tokens")
    if tokens is None:
        tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
    if not tokens:
        tokens = max(1, (len(prompt) + len(response.content)) // 4)
    return response.content.strip(), int(tokens)


def _is_provider_credit_error(error: Exception) -> bool:
    text = str(error).lower()
    return (
        "balance_insufficient" in text
        or "insufficient_quota" in text
        or "insufficient balance" in text
        or "error code: 402" in text
    )
