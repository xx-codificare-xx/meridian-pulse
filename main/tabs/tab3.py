# TAB 3 - TRANSCRIPTS

import os
import sys
import io
import json
import datetime
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(ROOT)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PATHS
from transcripts.transcript_handler import read_transcript, get_transcript_files


def tab_transcripts():
    st.markdown("### Transcript Intelligence")
    st.markdown("Select an earnings call transcript for an instant war room briefing.")
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    transcript_dir = PATHS["transcripts"]
    existing_files = get_transcript_files(transcript_dir)

    content  = ""
    filename = ""

    col_select, col_upload = st.columns([2, 1])

    with col_select:
        if existing_files:
            selected = st.selectbox("Select transcript", existing_files,
                                    help=f"From: {transcript_dir}")
            filepath = os.path.join(transcript_dir, selected)
            content  = read_transcript(filepath)
            filename = selected
        else:
            st.info(f"No transcripts found in: {transcript_dir}")

    with col_upload:
        uploaded = st.file_uploader("Upload new", type=["txt", "pdf", "docx"])
        if uploaded:
            save_path = os.path.join(transcript_dir, uploaded.name)
            with open(save_path, "wb") as f:
                f.write(uploaded.getbuffer())
            st.success(f"Saved: {uploaded.name}")
            st.rerun()

    if not content:
        st.markdown("""
        <div style='text-align:center;padding:3rem;opacity:0.4;'>
            <div style='font-size:1.1rem;'>Upload a transcript to begin intelligence briefing</div>
        </div>
        """, unsafe_allow_html=True)
        return

    st.caption(f"Transcript loaded: {len(content):,} characters")

    with st.expander("View raw transcript"):
        st.text(content[:3000])

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    if st.button("Run War Room Briefing", type="primary", use_container_width=True):
        with st.spinner("Meridian is analyzing the transcript..."):
            from engine.llm_handler import ask_llm, get_llm
            from engine.prompts import TRANSCRIPT_ANALYSIS_PROMPT
            llm = get_llm(role="scorer")
            try:
                raw    = ask_llm(TRANSCRIPT_ANALYSIS_PROMPT.format(transcript=content[:5000]), llm)
                raw    = raw.replace("```json", "").replace("```", "").strip()
                result = json.loads(raw)
                st.session_state["transcript_analysis"] = result
            except Exception as e:
                st.error(f"Analysis failed: {e}")

    analysis = st.session_state.get("transcript_analysis", {})

    if analysis:
        dark    = st.session_state.get("dark_mode", False)
        card_bg = "#1C1E26" if dark else "#FFFFFF"
        text_s  = "#9B9B9B" if dark else "#6B6B6B"
        border  = "#2E3140" if dark else "#E8E4DC"

        meta1, meta2, meta3 = st.columns(3)
        with meta1:
            st.markdown(f"**Company:** {analysis.get('company', 'Unknown')}")
        with meta2:
            st.markdown(f"**Period:** {analysis.get('period', 'Unknown')}")
        with meta3:
            speakers = analysis.get("speakers", [])
            st.markdown(f"**Speakers:** {len(speakers)}")

        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

        for card in [
            {"key": "pulse_check",    "title": "Pulse Check",    "color": "#1B4F8A", "type": "text"},
            {"key": "green_signals",  "title": "Green Signals",  "color": "#276749", "type": "list"},
            {"key": "red_signals",    "title": "Red Signals",    "color": "#CC0000", "type": "list"},
            {"key": "future_horizon", "title": "Future Horizon", "color": "#B8860B", "type": "list"},
            {"key": "data_spotlight", "title": "Data Spotlight", "color": "#6B3FA0", "type": "list"},
        ]:
            data = analysis.get(card["key"], [])
            if not data:
                continue
            if card["type"] == "text":
                content_html = f"<p style='color:{text_s};line-height:1.7;margin:0;'>{data}</p>"
            else:
                items = "".join([
                    f"<li style='color:{text_s};margin-bottom:0.4rem;'>{item}</li>"
                    for item in data
                ])
                content_html = f"<ul style='margin:0;padding-left:1.2rem;'>{items}</ul>"

            st.markdown(f"""
            <div style='background:{card_bg};border:1px solid {border};
                        border-radius:1rem;padding:1.5rem;margin-bottom:1rem;
                        border-left:4px solid {card["color"]};'>
                <div style='font-size:0.78rem;font-weight:600;letter-spacing:1px;
                            text-transform:uppercase;color:{card["color"]};margin-bottom:0.8rem;'>
                    {card["title"]}
                </div>
                {content_html}
            </div>
            """, unsafe_allow_html=True)

        if speakers:
            with st.expander("View all speakers"):
                for s in speakers:
                    st.markdown(f"- {s}")

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("#### Ask anything about this transcript")

    ex_cols = st.columns(5)
    for i, ex in enumerate([
        "Who are the speakers?",
        "Summarize in 25 words",
        "What did the CFO say about MLR?",
        "List all financial figures",
        "What are the key risks?",
    ]):
        with ex_cols[i]:
            if st.button(ex, key=f"ex_{i}", use_container_width=True):
                st.session_state["transcript_query"]     = ex
                st.session_state["transcript_submitted"] = True

    query = st.text_input(
        "Your question",
        value=st.session_state.get("transcript_query", ""),
        placeholder="Ask anything about this transcript...",
    )

    if query != st.session_state.get("transcript_query", ""):
        st.session_state["transcript_query"]     = query
        st.session_state["transcript_submitted"] = False

    if st.button("Ask Meridian", type="primary"):
        st.session_state["transcript_submitted"] = True

    if st.session_state.get("transcript_submitted") and st.session_state.get("transcript_query"):
        current_query = st.session_state["transcript_query"]
        st.session_state["transcript_submitted"] = False
        with st.spinner("Analyzing..."):
            from engine.llm_handler import ask_llm, get_llm
            from engine.prompts import TRANSCRIPT_QA_PROMPT
            llm      = get_llm(role="scorer")
            response = ask_llm(TRANSCRIPT_QA_PROMPT.format(
                query=current_query,
                transcript=content[:5000]
            ), llm)
            st.session_state["transcript_response"] = response

    response = st.session_state.get("transcript_response", "")
    if response:
        for section in response.split("\n\n"):
            for label in ["QUERY", "RESPONSE", "CONFIDENCE", "SOURCE"]:
                if section.startswith(label):
                    st.markdown(f"<div class='section-label'>{label.title()}</div>",
                                unsafe_allow_html=True)
                    body = section.replace(label, "").strip()
                    if label == "SOURCE":
                        st.markdown(f"> {body}")
                    else:
                        st.markdown(body)
                    break

        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(
                "Download TXT", response,
                file_name="meridian_transcript_insight.txt",
                mime="text/plain", use_container_width=True
            )
        with dl2:
            doc = __import__("docx").Document()
            doc.add_heading("Meridian Pulse", 0)
            doc.add_heading("Transcript Intelligence", 1)
            doc.add_paragraph(f"Query: {st.session_state.get('transcript_query', '')}")
            doc.add_paragraph(response)
            buf = io.BytesIO()
            doc.save(buf)
            buf.seek(0)
            st.download_button(
                "Download Word Doc", buf,
                file_name=f"meridian_transcript_{datetime.date.today()}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
