from __future__ import annotations

from config import LLM_MODELS

from .settings import settings


def get_llm(role: str = "scorer"):
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
        "max_tokens": 512,
    }
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def ask_llm(prompt: str, role: str = "scorer") -> str:
    response, _ = ask_llm_with_usage(prompt, role)
    return response


def ask_llm_with_usage(prompt: str, role: str = "scorer") -> tuple[str, int]:
    from langchain_core.messages import HumanMessage

    response = get_llm(role).invoke([HumanMessage(content=prompt)])
    usage = getattr(response, "usage_metadata", {}) or {}
    tokens = usage.get("total_tokens")
    if tokens is None:
        tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
    if not tokens:
        tokens = max(1, (len(prompt) + len(response.content)) // 4)
    return response.content.strip(), int(tokens)
