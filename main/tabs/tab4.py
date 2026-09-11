# TAB 4 - BEHIND MERIDIAN PULSE

import os
import sys
import base64
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(ROOT)


def tab_hire():
    qr_path = os.path.join(ROOT, "assets", "linkedin.png")
    try:
        with open(qr_path, "rb") as f:
            qr_b64 = base64.b64encode(f.read()).decode()
        qr_html = (
            "<img src='data:image/png;base64," + qr_b64 +
            "' style='border-radius:1rem;margin-top:1rem;width:200px;"
            "display:block;margin-left:auto;margin-right:auto;'/>"
        )
    except FileNotFoundError:
        qr_html = "<div style='color:#9B9B9B;font-size:0.8rem;'>QR image not found</div>"

    st.markdown(f"""
    <div class='hire-card'>
        <div class='hire-name'>Akansha Rawat</div>
        <div class='hire-role'>Healthcare AI and Strategy</div>
        <div class='divider'></div>
        <p style='color:#6B6B6B;font-size:0.95rem;line-height:1.8;text-align:center;
                  max-width:480px;margin:0 auto 1.5rem;'>
            Meridian Pulse was built to solve a real problem.
            BSC analysts spending 4 hours daily on manual news research.
            This tool brings that down to minutes using AI powered
            urgency scoring, live data pipelines, and intelligent filtering.
        </p>
        <div class='divider'></div>
        <a class='contact-link' href='mailto:amrawat@uci.edu'>
                Email
        </a>
        <a class='contact-link'
           href='https://www.linkedin.com/in/akansharawat01/'
           target='_blank'>
            LinkedIn
        </a>
        <div class='divider'></div>
        {qr_html}
        <div style='font-size:0.8rem;color:#9B9B9B;margin-top:0.8rem;text-align:center;'>
            Scan to connect on LinkedIn
        </div>
    </div>
    """, unsafe_allow_html=True)
