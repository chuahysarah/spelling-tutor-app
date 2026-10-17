from __future__ import annotations

import json
import requests
import streamlit as st

st.set_page_config(
    page_title="Parent Dashboard 📊",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Fixed sidebar labels/order; keep deployed filenames and app.py unchanged.
st.sidebar.page_link('app.py', label='Home')
st.sidebar.page_link('pages/1_📖_Learn_Words.py', label='Learn Words', icon='📖')
st.sidebar.page_link('pages/2_🎯_Dictation_Quiz.py', label='Dictation Quiz', icon='🎯')
st.sidebar.page_link('pages/5_More_Practices.py', label='Bookmarks', icon='🔖')
st.sidebar.page_link('pages/4_🌱_Word Garden.py', label='Word Garden', icon='🌱')
st.sidebar.page_link('pages/3_📊_Parent_Summary.py', label='Parent Summary', icon='📊')
st.sidebar.divider()

API_URL = st.secrets.get("GSHEETS_API_URL", "").strip()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700&display=swap');
:root { --ink:#26324b; --blue:#2864dc; --purple:#7652d6; --coral:#ff765e; --sun:#ffc94a; --mint:#36bca0; --sky:#e7f5ff; }
html, body, [class*="css"], button, input, select, textarea {
    font-family:'Fredoka',sans-serif !important; color:var(--ink);
}
html, body, [data-testid="stAppViewContainer"] { background:#fffaf0 !important; }
[data-testid="stHeader"] { background:rgba(255,250,240,.88) !important; }
[data-testid="stMainBlockContainer"] { max-width:1100px; padding-top:2rem; }
h1 { color:#3158b8 !important; font-weight:700 !important; letter-spacing:-.035em; }
h2 { color:#6746bd !important; font-weight:700 !important; }
h3 { color:#168d7c !important; font-weight:700 !important; }
.stButton > button {
    min-height:3.2rem; border:0 !important; border-radius:18px !important;
    background:linear-gradient(115deg,#ff795e 0%,#ff9f54 100%) !important;
    color:#fff !important; font-size:1.16rem !important; font-weight:700 !important;
    padding:.65rem 1.25rem !important; box-shadow:0 5px 0 #df624b,0 9px 18px rgba(223,98,75,.16) !important;
    transition:transform .16s ease,box-shadow .16s ease,filter .16s ease;
}
.stButton > button:hover { transform:translateY(-2px); filter:saturate(1.12); box-shadow:0 7px 0 #df624b,0 12px 22px rgba(223,98,75,.2) !important; }
.stButton > button:active { transform:translateY(2px); box-shadow:0 2px 0 #df624b !important; }
.stButton > button:focus-visible, input:focus-visible, textarea:focus-visible { outline:3px solid #3158b8 !important; outline-offset:3px; }
[data-testid="stSidebar"] {
    background:linear-gradient(165deg,#e6f4ff 0%,#f0eaff 55%,#fff0e8 100%) !important;
    border-right:3px solid #d6e5ff !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#34415c; }
[data-testid="stSidebarCollapseButton"] button {
    background:linear-gradient(135deg,#ffd34f,#ffad52) !important; color:#26324b !important;
    border:2px solid #efa83a !important; border-radius:12px !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background:#fff !important; border:2px solid #b8d9ff !important; border-radius:16px !important;
}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stSelectbox"] > div > div {
    border-radius:14px !important; border-color:#bdd8fa !important; background:#fff !important;
}
[data-testid="stExpander"] {
    background:rgba(255,255,255,.88); border:2px solid #e5dcfb !important; border-radius:18px !important;
}
[data-testid="stAlert"] { border-radius:16px !important; }
hr { border-color:#e6ddf7 !important; }
.hero {
    position:relative; overflow:hidden; padding:2.4rem 1.8rem; border-radius:30px;
    background:linear-gradient(125deg,#fff0ae 0%,#ffdfd7 48%,#d9eeff 100%);
    border:3px solid #fff; text-align:center; margin:0 0 1.7rem;
    box-shadow:0 12px 30px rgba(62,83,132,.12),inset 0 0 0 2px rgba(255,198,76,.6);
}
.hero h1 { color:#3158b8 !important; margin-bottom:.55rem; font-size:2.5rem !important; }
.hero p { color:#39445d; font-size:1.2rem; margin:0; }
.action-card {
    padding:1.45rem 1.2rem; min-height:155px; border-radius:24px;
    border:2px solid #fff; text-align:center;
    background:linear-gradient(145deg,#fff 0%,#eff8ff 100%);
    box-shadow:0 8px 22px rgba(53,86,144,.11),inset 0 0 0 2px #cde5ff;
}
.action-card h3 { font-size:1.65rem; color:#3158b8; margin-bottom:.4rem; }
.action-card p { font-size:1.05rem; color:#4b5872; }
@media (max-width:640px) {
    [data-testid="stMainBlockContainer"] { padding:1.1rem 1rem 2rem; }
    .hero { padding:1.6rem 1rem; border-radius:22px; }
    .hero h1 { font-size:2rem !important; }
}
@media (prefers-reduced-motion:reduce) { *,*::before,*::after { scroll-behavior:auto !important; transition:none !important; animation:none !important; } }

/* Child-friendly native sidebar controls. Keep Streamlit's own click/keyboard behavior. */
button[data-testid="stExpandSidebarButton"],
button[aria-label="Expand sidebar"],
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="collapsedControl"] button,
button[data-testid="stSidebarCollapsedControl"],
button[data-testid="collapsedControl"] {
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    gap:10px !important;
    width:auto !important;
    min-width:156px !important;
    min-height:56px !important;
    padding:10px 16px !important;
    background:#173f91 !important;
    color:#ffffff !important;
    border:3px solid #ffc94a !important;
    border-radius:16px !important;
    box-shadow:0 3px 0 #12336f,0 5px 14px rgba(17,24,39,.20) !important;
    opacity:1 !important;
    visibility:visible !important;
    cursor:pointer !important;
    transition:background-color .15s ease,box-shadow .15s ease !important;
}
button[data-testid="stExpandSidebarButton"]::after,
button[aria-label="Expand sidebar"]::after,
[data-testid="stSidebarCollapsedControl"] button::after,
[data-testid="collapsedControl"] button::after,
button[data-testid="stSidebarCollapsedControl"]::after,
button[data-testid="collapsedControl"]::after {
    content:"Open menu" !important;
    color:#ffffff !important;
    font:800 17px/1.2 'Nunito','Trebuchet MS',Arial,sans-serif !important;
    white-space:nowrap !important;
}
button[data-testid="stExpandSidebarButton"] span,
button[aria-label="Expand sidebar"] span,
[data-testid="stSidebarCollapsedControl"] button span,
[data-testid="collapsedControl"] button span {
    color:#ffffff !important;
    font-size:28px !important;
    opacity:1 !important;
}
button[data-testid="stExpandSidebarButton"] svg,
button[aria-label="Expand sidebar"] svg,
[data-testid="stSidebarCollapsedControl"] button svg,
[data-testid="collapsedControl"] button svg {
    width:28px !important;
    height:28px !important;
    color:#ffffff !important;
    opacity:1 !important;
}
button[data-testid="stExpandSidebarButton"]:hover,
button[aria-label="Expand sidebar"]:hover {
    background:#12336f !important;
    box-shadow:0 3px 0 #0c2451,0 6px 18px rgba(17,24,39,.24) !important;
}
button[data-testid="stExpandSidebarButton"]:focus-visible,
button[aria-label="Expand sidebar"]:focus-visible {
    outline:3px solid #111827 !important;
    outline-offset:3px !important;
}
[data-testid="stHeader"]:has(button[aria-label="Expand sidebar"]) {
    min-height:72px !important;
    overflow:visible !important;
}
/* Leave room below the visible menu control instead of covering page content. */
[data-testid="stAppViewContainer"]:has(button[aria-label="Expand sidebar"]) [data-testid="stMainBlockContainer"] {
    padding-top:5.25rem !important;
}
button[aria-label="Collapse sidebar"],
[data-testid="stSidebarCollapseButton"] button {
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    gap:6px !important;
    min-width:106px !important;
    min-height:48px !important;
    padding:8px 12px !important;
    background:#ffc94a !important;
    color:#111827 !important;
    border:2px solid #6b4e00 !important;
    border-radius:14px !important;
    opacity:1 !important;
    cursor:pointer !important;
}
button[aria-label="Collapse sidebar"]::after,
[data-testid="stSidebarCollapseButton"] button::after {
    content:"Close" !important;
    color:#111827 !important;
    font:800 16px/1.2 'Nunito','Trebuchet MS',Arial,sans-serif !important;
}
button[aria-label="Collapse sidebar"] span,
[data-testid="stSidebarCollapseButton"] button span {
    color:#111827 !important;
    font-size:26px !important;
    opacity:1 !important;
}
button[aria-label="Collapse sidebar"]:focus-visible {
    outline:3px solid #173f91 !important;
    outline-offset:3px !important;
}
@media (prefers-reduced-motion:reduce) {
    button[aria-label="Expand sidebar"],
    button[aria-label="Collapse sidebar"] { transition:none !important; }
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Parent Summary & Practice History")

PARENT_PIN = "6666"

if "parent_dashboard_unlocked" not in st.session_state:
    st.session_state.parent_dashboard_unlocked = False

if not st.session_state.parent_dashboard_unlocked:
    st.info("🔒 Enter PIN to view detailed learning history.")
    entered_pin = st.text_input("Enter 4-digit Parent PIN:", type="password", key="dash_pin_entry")
    if entered_pin == PARENT_PIN:
        st.session_state.parent_dashboard_unlocked = True
        st.rerun()
    elif entered_pin != "":
        st.error("❌ Incorrect PIN.")
    st.stop()


@st.cache_data(ttl=15, show_spinner=False)
def fetch_practice_history() -> list[dict]:
    if API_URL:
        try:
            resp = requests.get(f"{API_URL}?action=get_history", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []


@st.cache_data(ttl=15, show_spinner=False)
def fetch_child_profiles() -> list[str]:
    if API_URL:
        try:
            resp = requests.get(API_URL, params={"action": "get_profiles"}, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    return data
        except Exception:
            pass
    return ["Alex", "Emma"]


if "children" not in st.session_state:
    st.session_state.children = fetch_child_profiles()
if "active_child" not in st.session_state:
    st.session_state.active_child = st.session_state.children[0]

st.subheader("👤 Select Child Profile")
view_child = st.selectbox(
    "Showing active session details for:",
    options=st.session_state.children,
    index=st.session_state.children.index(st.session_state.active_child) if st.session_state.active_child in st.session_state.children else 0
)

st.divider()

st.subheader(f"🌟 Session Overview for {view_child}")
col1, col2 = st.columns(2)

mastered = st.session_state.get(f"mastered_words_{view_child}", set())
unfamiliar = st.session_state.get(f"unfamiliar_words_{view_child}", set())

with col1:
    st.metric(label="✅ Mastered Words (Session)", value=len(mastered))
    if mastered:
        st.write(", ".join(mastered))
    else:
        st.caption("No mastered words yet this session.")

with col2:
    st.metric(label="💡 Needs Practice (Session)", value=len(unfamiliar))
    if unfamiliar:
        st.write(", ".join(unfamiliar))
    else:
        st.caption("No practice flags currently.")

st.divider()

st.subheader("📜 All Recorded History Logs")

history = fetch_practice_history()

if history:
    filtered_history = [
        item for item in history 
        if item.get('child_name', '').casefold() == view_child.casefold() or not item.get('child_name')
    ]
    
    if filtered_history:
        for attempt in reversed(filtered_history):
            title = attempt.get('week_title', 'Spelling Practice')
            time_str = attempt.get('timestamp', 'N/A')
            score = attempt.get('score', 0)
            total = attempt.get('total_words', 0)
            with st.expander(f"🗓️ {time_str} — {title} (Score: {score}/{total})"):
                st.write(f"🎯 **Score:** {score} / {total}")
                st.write(f"✅ **Mastered Words:** {attempt.get('mastered', 'None')}")
                st.write(f"💡 **Needs Practice Words:** {attempt.get('unfamiliar', 'None')}")
    else:
        st.info(f"No history records found for {view_child} yet.")
else:
    st.info("No past practice logs found in database.")

if st.button("🔒 Lock Dashboard", type="secondary"):
    st.session_state.parent_dashboard_unlocked = False
    st.rerun()
