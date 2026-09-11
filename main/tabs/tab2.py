# TAB 2 - SEC INTELLIGENCE

import os
import sys
import streamlit as st  # type: ignore[import-not-found]

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(ROOT)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import TAGS, SEC_HEADERS
from components import render_card, render_pagination


def tab_sec():
    st.markdown("### SEC Filing Intelligence")
    st.markdown("Live competitor filings from UnitedHealth, Elevance, CVS, Humana, Cigna")
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    if st.button("Fetch SEC Filings", type="primary", use_container_width=True):
        with st.spinner("Pulling latest SEC filings..."):
            from ingestion.sec_fetcher import fetch_all_sec
            from engine.tag_scorer import score_all_articles
            selected_tags = st.session_state.get("selected_tags", list(TAGS.keys())[:3])
            filings = fetch_all_sec()
            scored  = score_all_articles(filings, selected_tags)
            st.session_state["sec_filings"] = scored
            st.session_state["sec_page"]    = 1

    filings = st.session_state.get("sec_filings", [])

    if not filings:
        st.markdown("""
        <div style='text-align:center;padding:4rem;opacity:0.4;'>
            <div style='font-size:1.1rem;'>Click fetch to load live SEC filings</div>
        </div>
        """, unsafe_allow_html=True)
        return

    col1, col2 = st.columns(2)
    with col1:
        company_filter = st.selectbox(
            "Filter by company",
            ["All"] + sorted(set(f["company"] for f in filings))
        )
    with col2:
        form_filter = st.selectbox(
            "Filter by filing type",
            ["All", "8-K", "10-K", "10-Q", "DEF 14A"]
        )

    filtered = filings
    if company_filter != "All":
        filtered = [f for f in filtered if f["company"] == company_filter]
    if form_filter != "All":
        filtered = [f for f in filtered if f["form_type"] == form_filter]

    start, end = render_pagination(len(filtered), "sec_page")

    for i, filing in enumerate(filtered[start:end]):
        render_card(filing, i)
        if st.button("Summarize with AI", key=f"sum_{filing['id']}", use_container_width=False):
            with st.spinner("Fetching and summarizing..."):
                try:
                    try:
                        from bs4 import BeautifulSoup
                    except ImportError:
                        st.error("The 'beautifulsoup4' package is required to parse SEC filing content.")
                        return

 
                    from urllib.request import Request, urlopen
                    from engine.llm_handler import ask_llm, get_llm
                    doc_url = filing.get("doc_url", "")
                    if not doc_url:
                        st.error("No SEC filing URL is available for this document.")
                        return
                    req = Request(doc_url, headers=SEC_HEADERS)
                    with urlopen(req, timeout=15) as response:
                        html = response.read().decode("utf-8", errors="replace")
                    soup = BeautifulSoup(html, "html.parser")
                    for tag in soup(["script", "style"]):
                        tag.decompose()
                    text = soup.get_text(separator=" ", strip=True)[:6000]
                    llm = get_llm(role="scorer")
                    prompt = f"""You are a healthcare strategy analyst at BCBS.
Analyze this SEC filing and provide:
1. What happened (2-3 sentences)
2. Key financial figures mentioned
3. Strategic implications for BSC
4. Urgency level and why

Filing:
{text}"""
                    summary = ask_llm(prompt, llm)
                    st.markdown("#### AI Filing Summary")
                    st.markdown(summary)
                except Exception as e:
                    st.error(f"Could not summarize: {e}")
