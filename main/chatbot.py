# CHATBOT

import os
import sys
import streamlit as st
import streamlit.components.v1 as components

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_chatbot_component = components.declare_component(
    "meridian_chatbot",
    path=os.path.join(os.path.dirname(__file__), "chatbot_component"),
)

def render_sidebar_chat():
    """Render the chatbot as a floating custom Streamlit component.

    The function name remains unchanged so the app entrypoint does not need
    to change. Existing chat history and LLM behavior are preserved.
    """
    if "sidebar_chat" not in st.session_state:
        st.session_state["sidebar_chat"] = []
    if "chat_open" not in st.session_state:
        st.session_state["chat_open"] = False

    articles = st.session_state.get("articles", [])
    if articles:
        context = "\n".join([
            f"- [{a.get('urgency_label','')}] {a.get('title','')} "
            f"({a.get('source','')}, {a.get('published','')}): "
            f"{a.get('reasoning','')}"
            for a in articles[:20]
        ])
    else:
        context = "No articles fetched yet."

    event = _chatbot_component(
        messages=st.session_state["sidebar_chat"],
        open=st.session_state["chat_open"],
        dark=st.session_state.get("dark_mode", False),
        article_count=len(articles),
        height=650 if st.session_state["chat_open"] else 90,
        key="meridian_chatbot",
        default=None,
    )

    if not event:
        return

    event_type = event.get("type")
    if event_type == "toggle":
        st.session_state["chat_open"] = bool(event.get("open", False))
        st.rerun()
    elif event_type == "clear":
        st.session_state["sidebar_chat"] = []
        st.rerun()
    elif event_type == "submit":
        query = str(event.get("query", "")).strip()
        if not query:
            return

        st.session_state["sidebar_chat"].append({"role": "user", "content": query})
        history = "\n".join([
            f"{m['role'].upper()}: {m['content']}"
            for m in st.session_state["sidebar_chat"][-6:]
        ])
        with st.spinner("Thinking..."):
            try:
                from engine.llm_handler import ask_llm, get_llm
                from engine.prompts import CHATBOT_PROMPT
                llm = get_llm(role="scorer")
                response = ask_llm(CHATBOT_PROMPT.format(
                    context=context,
                    history=history,
                    query=query,
                ), llm)
            except Exception as e:
                response = f"Meridian error: {e}"
        st.session_state["sidebar_chat"].append(
            {"role": "assistant", "content": response}
        )
        st.session_state["chat_open"] = True
        st.rerun()
