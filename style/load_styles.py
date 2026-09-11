import streamlit as st


def load_styles(dark_mode: bool):
    bg          = "#0F1117" if dark_mode else "#F8F5F0"
    card_bg     = "#1C1E26" if dark_mode else "#FFFFFF"
    text_primary= "#F0EEE9" if dark_mode else "#1A1A1A"
    text_sec    = "#9B9B9B" if dark_mode else "#6B6B6B"
    accent      = "#4A90D9" if dark_mode else "#1B4F8A"
    border      = "#2E3140" if dark_mode else "#E8E4DC"
    tab_bg      = "#1C1E26" if dark_mode else "#FFFFFF"
    chip_bg     = "#2E3140" if dark_mode else "#EEF2F7"
    user_bubble = "#2E3140" if dark_mode else "#EEF2F7"
    bot_bubble  = "#1C1E26" if dark_mode else "#FFFFFF"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {{
        background-color: {bg} !important;
        color: {text_primary} !important;
        font-family: 'Inter', sans-serif;
    }}

    #MainMenu, footer, header {{ visibility: hidden; }}
    .block-container {{ padding-top: 0rem !important; }}

    @keyframes fadeSlideUp {{
        from {{ opacity: 0; transform: translateY(30px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50%       {{ opacity: 0.6; }}
    }}
    @keyframes gradientShift {{
        0%   {{ background-position: 0% 50%; }}
        50%  {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}

    .hero {{
        background: linear-gradient(-45deg,
            {'#0a0e1a, #1a2340, #0d1b2a, #162032' if dark_mode else '#e8f4f8, #f0e8f8, #e8f0f8, #f8f0e8'});
        background-size: 400% 400%;
        animation: gradientShift 8s ease infinite;
        padding: 3rem 2rem 2rem;
        border-radius: 0 0 2rem 2rem;
        margin-bottom: 2rem;
        text-align: center;
    }}
    .hero-title {{
        font-family: 'Playfair Display', serif;
        font-size: 3.5rem;
        font-weight: 700;
        color: {accent};
        animation: fadeSlideUp 1s ease forwards;
        margin-bottom: 0.5rem;
        letter-spacing: -1px;
    }}
    .hero-tagline {{
        font-size: 1rem;
        color: {text_sec};
        font-weight: 300;
        animation: fadeSlideUp 1.2s ease forwards;
        letter-spacing: 3px;
        text-transform: uppercase;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        background: {tab_bg};
        border-radius: 1rem;
        padding: 0.3rem;
        gap: 0.2rem;
        border: 1px solid {border};
        margin: 0 1rem 1.5rem;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 0.7rem;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        font-size: 0.9rem;
        color: {text_sec};
        padding: 0.6rem 1.5rem;
        transition: all 0.3s ease;
    }}
    .stTabs [aria-selected="true"] {{
        background: {accent} !important;
        color: white !important;
    }}

    .news-card {{
        background: {card_bg};
        border: 1px solid {border};
        border-radius: 1rem;
        padding: 1.5rem;
        margin-bottom: 1rem;
        animation: fadeSlideUp 0.6s ease forwards;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .news-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
    }}

    .badge {{
        display: inline-block;
        padding: 0.25rem 0.8rem;
        border-radius: 2rem;
        font-size: 0.72rem;
        font-weight: 600;
        margin-bottom: 0.8rem;
        letter-spacing: 0.8px;
        text-transform: uppercase;
    }}
    .badge-high    {{ background: #FFF0F0; color: #CC0000; border: 1px solid #FFB3B3; }}
    .badge-medium  {{ background: #FFFBF0; color: #B8860B; border: 1px solid #FFE082; }}
    .badge-low     {{ background: #F0FFF4; color: #276749; border: 1px solid #A8D5B5; }}
    .badge-minimal {{ background: #F5F5F5; color: #555555; border: 1px solid #CCCCCC; }}
    .pulse-high    {{ animation: pulse 2s ease-in-out infinite; }}

    .card-title {{
        font-family: 'Playfair Display', serif;
        font-size: 1.1rem;
        font-weight: 600;
        color: {text_primary};
        margin-bottom: 0.5rem;
        line-height: 1.4;
    }}
    .card-meta {{
        font-size: 0.8rem;
        color: {text_sec};
        margin-bottom: 0.8rem;
    }}
    .card-reasoning {{
        font-size: 0.88rem;
        color: {text_sec};
        line-height: 1.6;
        border-left: 3px solid {accent};
        padding-left: 0.8rem;
        margin-top: 0.8rem;
    }}
    .score-bar-bg {{
        background: {border};
        border-radius: 1rem;
        height: 6px;
        margin-top: 0.8rem;
    }}
    .score-bar-fill {{
        height: 6px;
        border-radius: 1rem;
        background: linear-gradient(90deg, {accent}, #E74C3C);
    }}
    .tag-chip {{
        display: inline-block;
        background: {chip_bg};
        color: {accent};
        border-radius: 1rem;
        padding: 0.2rem 0.7rem;
        font-size: 0.75rem;
        margin: 0.2rem;
        font-weight: 500;
    }}
    .divider {{
        height: 1px;
        background: {border};
        margin: 1.5rem 0;
    }}
    .section-label {{
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: {accent};
        margin-bottom: 0.3rem;
    }}
    .hire-card {{
        background: {card_bg};
        border: 1px solid {border};
        border-radius: 1.5rem;
        padding: 3rem;
        text-align: center;
        max-width: 600px;
        margin: 2rem auto;
        animation: fadeSlideUp 0.8s ease forwards;
    }}
    .hire-name {{
        font-family: 'Playfair Display', serif;
        font-size: 2rem;
        font-weight: 700;
        color: {accent};
        margin-bottom: 0.5rem;
    }}
    .hire-role {{
        font-size: 0.9rem;
        color: {text_sec};
        margin-bottom: 2rem;
        letter-spacing: 2px;
        text-transform: uppercase;
    }}
    .contact-link {{
        display: block;
        color: {accent};
        text-decoration: none;
        font-size: 1rem;
        margin: 0.5rem 0;
        font-weight: 500;
    }}
    .chat-bubble-user {{
        background: {user_bubble};
        border-radius: 1rem 1rem 0.2rem 1rem;
        padding: 0.7rem 1rem;
        margin-bottom: 0.5rem;
        font-size: 0.88rem;
        text-align: right;
        color: {text_primary};
    }}
    .chat-bubble-bot {{
        background: {bot_bubble};
        border: 1px solid {border};
        border-left: 3px solid {accent};
        border-radius: 1rem 1rem 1rem 0.2rem;
        padding: 0.7rem 1rem;
        margin-bottom: 0.5rem;
        font-size: 0.88rem;
        line-height: 1.6;
        color: {text_primary};
    }}
    [data-testid="stSidebar"] {{ display: block !important; visibility: visible !important; }}
    [data-testid="collapsedControl"] {{ display: block !important; visibility: visible !important; }}
    </style>
    """, unsafe_allow_html=True)
