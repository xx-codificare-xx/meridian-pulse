import os
import sys
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import APP_TITLE, APP_TAGLINE

ARTICLES_PER_PAGE = 15
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def render_hero():
    import base64
    logo_path = os.path.join(ROOT, "assets", "logo.png")
    try:
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        logo_src = f"data:image/png;base64,{logo_b64}"
    except FileNotFoundError:
        logo_src = "https://via.placeholder.com/64x64/1B4F8A/FFFFFF?text=M"

    st.markdown(f"""
    <div class="hero">
        <img src="{logo_src}"
             style="border-radius:100%;width:120px;height:120px;
                    margin-bottom:1rem;display:block;
                    margin-left:auto;margin-right:auto;"/>
        <div class="hero-title">{APP_TITLE}</div>
        <div class="hero-tagline">{APP_TAGLINE}</div>
    </div>
    """, unsafe_allow_html=True)

def get_badge(label: str) -> str:
    mapping = {
        "🔴 High":    ("high",    "High Priority"),
        "🟡 Medium":  ("medium",  "Medium"),
        "🟢 Low":     ("low",     "Low"),
        "🔵 Minimal": ("minimal", "Minimal"),
        "Unscored":   ("minimal", "Unscored"),
    }
    cls, text = mapping.get(label, ("minimal", label))
    pulse = " pulse-high" if cls == "high" else ""
    return f'<span class="badge badge-{cls}{pulse}">{text}</span>'

def render_card(article: dict, idx: int):
    badge     = get_badge(article.get("urgency_label", "Unscored"))
    score     = article.get("urgency_score", 0.0)
    score_pct = int(score * 100)
    tags      = article.get("tags_matched", [])
    reasoning = article.get("reasoning", "")
    source    = article.get("source", "")
    published = article.get("published", "")
    title     = article.get("title", "Untitled")
    url       = article.get("url", "#")
    tag_chips = "".join([f'<span class="tag-chip">{t}</span>' for t in tags]) if tags else ""

    st.markdown(f"""
    <div class="news-card" style="animation-delay:{idx*0.08}s">
        {badge}
        <div class="card-title">{title}</div>
        <div class="card-meta">{source} &nbsp;&nbsp; {published}</div>
        <div class="score-bar-bg">
            <div class="score-bar-fill" style="width:{score_pct}%"></div>
        </div>
        <div style="font-size:0.75rem;margin-top:0.3rem;color:#888;">
            Urgency score: {score_pct}%
        </div>
        {f'<div class="card-reasoning">{reasoning}</div>' if reasoning else ''}
        {f'<div style="margin-top:0.8rem">{tag_chips}</div>' if tag_chips else ''}
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Read more"):
        st.markdown(f"**Source:** {source}")
        st.markdown(f"**Published:** {published}")
        st.markdown(f"**Summary:** {article.get('summary', '')}")
        st.markdown(f"[Open full article]({url})")

def render_pagination(total: int, page_key: str):
    total_pages = max(1, (total + ARTICLES_PER_PAGE - 1) // ARTICLES_PER_PAGE)
    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    current_page = st.session_state[page_key]
    if current_page < 1:
        current_page = 1
        st.session_state[page_key] = 1
    if current_page > total_pages:
        current_page = total_pages
        st.session_state[page_key] = total_pages

    col_prev, col_mid, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("← Prev", key=f"{page_key}_prev", disabled=current_page == 1, use_container_width=True):
            st.session_state[page_key] = max(1, current_page - 1)
    with col_mid:
        st.markdown(f"<div style='text-align:center; font-weight:600; padding-top:0.45rem;'>Page {current_page}/{total_pages}</div>", unsafe_allow_html=True)
    with col_next:
        if st.button("Next →", key=f"{page_key}_next", disabled=current_page >= total_pages, use_container_width=True):
            st.session_state[page_key] = min(total_pages, current_page + 1)

    start = (current_page - 1) * ARTICLES_PER_PAGE
    end = start + ARTICLES_PER_PAGE
    return start, end
