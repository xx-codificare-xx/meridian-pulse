import os
import sys
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LLM_MODELS
from engine.prompts import PREFILTER_PROMPT


# def get_llm():
#     """Returns configured LLM client — swap provider in config.py only."""
#     if LLM_PROVIDER == "anthropic":
#         from langchain_anthropic import ChatAnthropic
#         return ChatAnthropic(
#             model=LLM_MODEL_ANTHROPIC,
#             api_key=ANTHROPIC_API_KEY,
#             max_tokens=512,
#         )
#     elif LLM_PROVIDER == "openai":
#         from langchain_openai import ChatOpenAI
#         return ChatOpenAI(
#             model=LLM_MODEL_OPENAI,
#             api_key=OPENAI_API_KEY,
#             max_tokens=512,
#         )
#     else:
#         raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")
def get_llm(role="scorer"):
    load_dotenv()
    from config import (
        API_MODE,
        AI_CREDITS_BASE_URL,
        LLM_MODEL_PREFILTER,
        LLM_MODEL_SCORER,
        LLM_PROVIDER,
    )

    api_mode = os.getenv("LLM_API_MODE", os.getenv("API_MODE", API_MODE)).lower()
    ai_credits_key = os.getenv("LLM_API_KEY", os.getenv("AI_CREDITS_KEY", ""))
    openai_direct_key = os.getenv("OPENAI_DIRECT_KEY", "")
    ai_credits_base_url = os.getenv(
        "LLM_BASE_URL",
        os.getenv("AI_CREDITS_BASE_URL", AI_CREDITS_BASE_URL),
    )
    #model = LLM_MODELS[LLM_PROVIDER][role]
    
    from langchain_openai import ChatOpenAI

    if api_mode in {"openai_direct", "openai"}:
        # Goes straight to OpenAI — only openai models work here
        model = LLM_MODELS["openai"][role]
        return ChatOpenAI(
            model=model,
            api_key=openai_direct_key,
            max_tokens=512,
        )
    elif api_mode in {"aicredits", "ai_credits"}:
        # AI Credits proxy — supports both openai and anthropic models
        model = {
            "prefilter": LLM_MODEL_PREFILTER,
            "scorer": LLM_MODEL_SCORER,
        }.get(role)
        if not model:
            raise ValueError(f"Unknown LLM role: {role}")
        return ChatOpenAI(
            model=model,
            api_key=ai_credits_key,
            base_url=ai_credits_base_url,
            max_tokens=512,
        )
    else:
        raise ValueError(
            "Unsupported LLM_API_MODE. Use 'aicredits' or 'openai_direct'."
        )


def ask_llm(prompt: str, llm=None) -> str:
    """Send a prompt, get a string response back."""
    if llm is None:
        llm = get_llm()
    from langchain_core.messages import HumanMessage
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip()


def is_healthcare_relevant(article: dict, llm=None) -> bool:
    prompt = PREFILTER_PROMPT.format(
        title=article.get("title", ""),
        summary=article.get("summary", "")[:300]
    )
    try:
        if llm is None:
            llm = get_llm(role="prefilter")
        answer = ask_llm(prompt, llm)
        return answer.strip().upper().startswith("YES")
    except Exception as e:
        print(f"[LLM] Pre-filter error: {e}")
        return True


if __name__ == "__main__":
    test = {
        "title": "Florida hospitals win $8 billion in extra Medicaid funds",
        "summary": "Florida hospitals are set to receive billions in additional Medicaid funding before federal limits take effect."
    }
    result = is_healthcare_relevant(test)
    print(f"Relevant: {result}")