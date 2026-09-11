#MAIN APP

import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import APP_TITLE
from style.load_styles import load_styles
from main.components import render_hero
from chatbot import render_sidebar_chat
from main.tabs.tab1 import tab_dashboard
from main.tabs.tab2 import tab_sec
from main.tabs.tab3 import tab_transcripts
from main.tabs.tab4 import tab_hire

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="M",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    if "dark_mode" not in st.session_state:
        st.session_state["dark_mode"] = False

    col1, col2 = st.columns([10, 1])
    with col2:
        dark = st.toggle("Night", value=st.session_state["dark_mode"])
        st.session_state["dark_mode"] = dark

    load_styles(dark)
    render_hero()

    tab1, tab2, tab3, tab4 = st.tabs([
        "Urgency Dashboard",
        "SEC Intelligence",
        "Transcripts",
        "Behind Meridian Pulse",
    ])

    with tab1:
        tab_dashboard()
    with tab2:
        tab_sec()
    with tab3:
        tab_transcripts()
    with tab4:
        tab_hire()

    render_sidebar_chat()


if __name__ == "__main__":
    main()
