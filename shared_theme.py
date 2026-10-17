"""Shared visual theme matching app.py. Styling only; no application logic."""

import streamlit as st


def apply_shared_theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700;800&family=Nunito:wght@400;500;600;700;800&display=swap');
        :root {
            --ink:#111827; --body:#1f2937; --blue:#173f91; --blue-dark:#12336f;
            --purple:#4b1d82; --coral:#ff765e; --sun:#ffc94a; --mint:#36bca0;
            --sky:#e6f4ff; --cream:#fffefa; --surface:#ffffff; --focus:#ffc000;
            --control-border:#64748b;
        }
        html, body, [class*="css"], button, input, select, textarea {
            font-family:'Nunito','Trebuchet MS',Arial,sans-serif !important;
            color:var(--ink);
        }
        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
            background:var(--cream) !important;
        }
        [data-testid="stHeader"] { background:rgba(255,250,240,.94) !important; }
        [data-testid="stMainBlockContainer"] { max-width:1100px; padding:2rem 1rem; }
        p, li, [data-testid="stMarkdownContainer"] p {
            color:var(--body) !important; font-size:1.125rem; line-height:1.5; font-weight:500;
        }
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stCaptionContainer"],
        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] label {
            color:#1f2937 !important; opacity:1 !important;
        }
        [data-testid="stCaptionContainer"] { font-size:1rem !important; font-weight:500; }
        h1, [data-testid="stMarkdownContainer"] h1 {
            color:var(--blue) !important; font:800 2rem/1.2 'Baloo 2','Trebuchet MS',sans-serif !important;
            letter-spacing:-.02em;
        }
        /* Standalone page titles use the same centered hero treatment as Home. */
        [data-testid="stMainBlockContainer"] h1 {
            display:block; width:100%; box-sizing:border-box; text-align:center !important;
            margin:.45rem 0 1.25rem !important; padding:1rem 1.25rem !important;
            border:2px solid #c6a14e; border-radius:24px;
            background:linear-gradient(125deg,#fff0ae 0%,#ffdfd7 48%,#d9eeff 100%);
            box-shadow:0 8px 22px rgba(62,83,132,.10);
        }
        h2, [data-testid="stMarkdownContainer"] h2 {
            color:var(--purple) !important; font:800 1.625rem/1.25 'Baloo 2','Trebuchet MS',sans-serif !important;
        }
        h3, [data-testid="stMarkdownContainer"] h3 {
            color:#07594f !important; font:800 1.375rem/1.3 'Baloo 2','Trebuchet MS',sans-serif !important;
        }
        [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label {
            color:var(--ink) !important; font-size:1.125rem !important; line-height:1.4; font-weight:700;
        }
        .stButton > button, [data-testid="stFormSubmitButton"] button,
        button[data-testid^="stBaseButton-"] {
            display:flex !important; align-items:center !important; justify-content:center !important;
            text-align:center !important; white-space:normal !important;
            min-height:2.75rem; border:2px solid var(--blue) !important; border-radius:16px !important;
            padding:.65rem 1.15rem !important; background:var(--blue) !important; color:#fff !important;
            font:700 1.125rem 'Nunito','Trebuchet MS',Arial,sans-serif !important;
            box-shadow:0 4px 0 var(--blue-dark),0 8px 16px rgba(49,88,184,.15) !important;
            transition:transform .15s ease,box-shadow .15s ease,background-color .15s ease;
        }
        /* Streamlit nests button labels in inner div/span/p nodes; set text color there too. */
        .stButton > button *, [data-testid="stFormSubmitButton"] button *,
        button[data-testid^="stBaseButton-"] * {
            color:#fff !important; font-family:'Nunito','Trebuchet MS',Arial,sans-serif !important;
            text-align:center !important;
        }
        .stButton > button > div, [data-testid="stFormSubmitButton"] button > div,
        button[data-testid^="stBaseButton-"] > div {
            display:flex !important; align-items:center !important; justify-content:center !important;
            width:100%;
        }
        .stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {
            background:var(--blue-dark) !important; border-color:var(--blue-dark) !important; transform:translateY(-1px);
        }
        .stButton > button:active, [data-testid="stFormSubmitButton"] button:active {
            transform:translateY(2px); box-shadow:0 1px 0 var(--blue-dark) !important;
        }
        [data-testid="stSidebar"] {
            background:linear-gradient(165deg,#e6f4ff 0%,#f0eaff 55%,#fff0e8 100%) !important;
            border-right:3px solid #d6e5ff !important;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:var(--body) !important; }
        [data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
            background:#fff !important; border:2px solid var(--control-border) !important; border-radius:16px !important;
        }
        [data-testid="stSidebarCollapseButton"] button {
            min-width:2.75rem; min-height:2.75rem; background:#ffc94a !important; color:var(--ink) !important;
            border:2px solid #6b4e00 !important; border-radius:12px !important;
        }
        [data-testid="stSidebarCollapsedControl"] button, [data-testid="collapsedControl"] button,
        button[data-testid="stSidebarCollapsedControl"], button[data-testid="collapsedControl"] {
            display:flex !important; align-items:center !important; justify-content:center !important; gap:.5rem !important;
            min-width:8.25rem !important; min-height:3rem !important; padding:.55rem .8rem !important;
            border:2px solid #ffc000 !important; border-radius:14px !important; background:#173f91 !important;
            color:#fff !important; box-shadow:0 3px 0 #12336f,0 5px 12px rgba(17,24,39,.2) !important;
            cursor:pointer !important;
        }
        [data-testid="stSidebarCollapsedControl"] button::after, [data-testid="collapsedControl"] button::after,
        button[data-testid="stSidebarCollapsedControl"]::after, button[data-testid="collapsedControl"]::after {
            content:'Open menu'; color:#fff !important; font:700 1rem 'Nunito','Trebuchet MS',Arial,sans-serif !important;
            white-space:nowrap;
        }
        [data-testid="stSidebarCollapsedControl"] button svg, [data-testid="collapsedControl"] button svg,
        button[data-testid="stSidebarCollapsedControl"] svg, button[data-testid="collapsedControl"] svg {
            width:1.25rem !important; height:1.25rem !important; color:#fff !important; stroke:#fff !important;
        }
        [data-testid="stSidebarCollapsedControl"] button:hover, [data-testid="collapsedControl"] button:hover {
            background:#12336f !important; transform:translateY(-1px);
        }
        [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
        [data-testid="stSelectbox"] > div > div {
            min-height:2.75rem; border-radius:14px !important; border:2px solid var(--control-border) !important;
            background:#fff !important; color:var(--ink) !important; font-size:1.125rem !important; font-weight:600;
        }
        [data-testid="stTextInput"] input::placeholder, [data-testid="stTextArea"] textarea::placeholder {
            color:#374151 !important; opacity:1;
        }
        [data-testid="stExpander"] { background:rgba(255,255,255,.92); border:2px solid #e5dcfb !important; border-radius:18px !important; }
        [data-testid="stAlert"] { border-radius:16px !important; }
        [data-testid="stMetric"] {
            padding:1rem 1.1rem; border:2px solid #c6d7f2; border-radius:20px;
            background:linear-gradient(145deg,#fff,#edf5ff); box-shadow:0 5px 14px rgba(23,63,145,.08);
        }
        [data-testid="stMetricLabel"] p { color:#1f2937 !important; font-weight:800 !important; }
        [data-testid="stMetricValue"] { color:#111827 !important; font-family:'Baloo 2','Trebuchet MS',sans-serif !important; }
        [data-testid="stProgress"] > div > div { background:#173f91 !important; }
        :is(button,input,textarea,[role="combobox"]):focus-visible { outline:3px solid #ffc000 !important; outline-offset:3px !important; }
        hr { border-color:#e6ddf7 !important; }
        @media (max-width:640px) {
            [data-testid="stMainBlockContainer"] { padding:1.1rem 1rem 2rem; }
            [data-testid="stMainBlockContainer"] h1 { padding:.85rem .75rem !important; font-size:1.65rem !important; }
            .stButton > button, [data-testid="stFormSubmitButton"] button,
            button[data-testid^="stBaseButton-"] { width:100% !important; min-height:48px !important; }
            [data-testid="stHorizontalBlock"] { flex-direction:column !important; gap:.7rem !important; }
            [data-testid="stHorizontalBlock"] [data-testid="stColumn"] { width:100% !important; min-width:100% !important; }
        }
        @media (prefers-reduced-motion:reduce) {
            *,*::before,*::after { scroll-behavior:auto !important; transition:none !important; animation:none !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
