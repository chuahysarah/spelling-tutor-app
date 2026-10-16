from __future__ import annotations

import json
import requests
import streamlit as st
from html import escape

st.set_page_config(
    page_title="Magic Spelling World ✏️",
    page_icon="⭐",
    layout="centered",
    initial_sidebar_state="auto"
)

# Fixed sidebar labels/order; keep deployed filenames and app.py unchanged.
st.sidebar.page_link('app.py', label='Home')
st.sidebar.page_link('pages/1_📖_Learn_Words.py', label='Learn Words', icon='📖')
st.sidebar.page_link('pages/2_🎯_Dictation_Quiz.py', label='Dictation Quiz', icon='🎯')
st.sidebar.page_link('pages/5_More_Practices.py', label='More Practices')
st.sidebar.page_link('pages/4_🌱_Word Garden.py', label='Word Garden', icon='🌱')
st.sidebar.page_link('pages/3_📊_Parent_Summary.py', label='Parent Summary', icon='📊')
st.sidebar.divider()

API_URL = st.secrets.get("GSHEETS_API_URL", "").strip()

st.markdown("""
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

/* Comfortable default text sizes and clearly differentiated headings. */
p, li, [data-testid="stMarkdownContainer"] p {
    color:var(--body) !important; font-size:1.125rem; line-height:1.5; font-weight:500;
}

/* Make Streamlit-rendered supporting text consistently dark and fully opaque. */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stCaptionContainer"],
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label {
    color:#1f2937 !important;
    opacity:1 !important;
}
[data-testid="stCaptionContainer"] { font-size:1rem !important; font-weight:500; }
h1, [data-testid="stMarkdownContainer"] h1 {
    color:var(--blue) !important; font-size:2rem !important;
    font-family:'Baloo 2','Trebuchet MS',sans-serif !important;
    line-height:1.2; font-weight:800 !important; letter-spacing:-.02em;
}
h2, [data-testid="stMarkdownContainer"] h2 {
    color:var(--purple) !important; font-size:1.625rem !important;
    font-family:'Baloo 2','Trebuchet MS',sans-serif !important;
    line-height:1.25; font-weight:800 !important;
}
h3, [data-testid="stMarkdownContainer"] h3 {
    color:#07594f !important; font-size:1.375rem !important;
    font-family:'Baloo 2','Trebuchet MS',sans-serif !important;
    line-height:1.3; font-weight:800 !important;
}
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label {
    color:var(--ink) !important; font-size:1.125rem !important;
    line-height:1.4; font-weight:700;
}

/* High-contrast primary buttons; colorful gradients remain in supporting surfaces. */
.stButton > button,
[data-testid="stFormSubmitButton"] button {
    min-height:2.75rem; border:2px solid var(--blue) !important;
    border-radius:16px !important; padding:.65rem 1.15rem !important;
    background:var(--blue) !important; color:#fff !important;
    font-family:'Nunito','Trebuchet MS',Arial,sans-serif !important;
    font-size:1.125rem !important; font-weight:700 !important;
    box-shadow:0 4px 0 var(--blue-dark),0 8px 16px rgba(49,88,184,.15) !important;
    transition:transform .15s ease,box-shadow .15s ease,background-color .15s ease;
}
.stButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover {
    background:var(--blue-dark) !important; border-color:var(--blue-dark) !important;
    transform:translateY(-1px);
}
.stButton > button:active,
[data-testid="stFormSubmitButton"] button:active {
    transform:translateY(2px); box-shadow:0 1px 0 var(--blue-dark) !important;
}

/* Sidebar and controls retain the colorful child-friendly treatment. */
[data-testid="stSidebar"] {
    background:linear-gradient(165deg,#e6f4ff 0%,#f0eaff 55%,#fff0e8 100%) !important;
    border-right:3px solid #d6e5ff !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:var(--body) !important; }
[data-testid="stSidebarCollapseButton"] button {
    min-width:2.75rem; min-height:2.75rem;
    background:linear-gradient(135deg,#ffd34f,#ffad52) !important;
    color:var(--ink) !important; border:2px solid #6b4e00 !important;
    border-radius:12px !important;
}
/* The collapsed-sidebar control is easy to miss on phones; make its action explicit. */
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="collapsedControl"] button,
button[data-testid="stSidebarCollapsedControl"],
button[data-testid="collapsedControl"] {
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    gap:.5rem !important;
    min-width:8.25rem !important;
    min-height:3rem !important;
    padding:.55rem .8rem !important;
    border:2px solid #ffc000 !important;
    border-radius:14px !important;
    background:#173f91 !important;
    color:#ffffff !important;
    box-shadow:0 3px 0 #12336f,0 5px 12px rgba(17,24,39,.2) !important;
    cursor:pointer !important;
}
[data-testid="stSidebarCollapsedControl"] button::after,
[data-testid="collapsedControl"] button::after,
button[data-testid="stSidebarCollapsedControl"]::after,
button[data-testid="collapsedControl"]::after {
    content:"Open menu";
    color:#ffffff !important;
    font-family:'Nunito','Trebuchet MS',Arial,sans-serif !important;
    font-size:1rem !important;
    font-weight:700 !important;
    white-space:nowrap;
}
[data-testid="stSidebarCollapsedControl"] button svg,
[data-testid="collapsedControl"] button svg,
button[data-testid="stSidebarCollapsedControl"] svg,
button[data-testid="collapsedControl"] svg {
    width:1.25rem !important;
    height:1.25rem !important;
    color:#ffffff !important;
    stroke:#ffffff !important;
}
[data-testid="stSidebarCollapsedControl"] button:hover,
[data-testid="collapsedControl"] button:hover,
button[data-testid="stSidebarCollapsedControl"]:hover,
button[data-testid="collapsedControl"]:hover {
    background:#12336f !important;
    transform:translateY(-1px);
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background:#fff !important; border:2px solid var(--control-border) !important;
    border-radius:16px !important;
}
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] > div > div {
    min-height:2.75rem; border-radius:14px !important;
    border:2px solid var(--control-border) !important; background:#fff !important;
    color:var(--ink) !important; font-size:1.125rem !important; font-weight:600;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder {
    color:#374151 !important; opacity:1;
}
[data-testid="stExpander"] {
    background:rgba(255,255,255,.92); border:2px solid #e5dcfb !important;
    border-radius:18px !important;
}
[data-testid="stAlert"] { border-radius:16px !important; }
hr { border-color:#e6ddf7 !important; }

/* Existing home-page component classes, retained from your app. */
.hero {
    position:relative; overflow:hidden; padding:2.4rem 1.8rem;
    border-radius:30px;
    background:linear-gradient(125deg,#fff0ae 0%,#ffdfd7 48%,#d9eeff 100%);
    border:3px solid #fff; text-align:center; margin:0 0 1.7rem;
    box-shadow:0 12px 30px rgba(62,83,132,.12),inset 0 0 0 2px rgba(255,198,76,.6);
}
.hero h1 {
    color:var(--blue) !important; margin-bottom:.55rem;
    font-family:'Baloo 2','Trebuchet MS',sans-serif !important;
    font-size:2.5rem !important; font-weight:800 !important;
}
.hero p { color:var(--ink) !important; font-size:1.2rem; font-weight:700; margin:0; }
.child-name {
    display:inline-block; white-space:nowrap;
    margin:0 .08em; padding:0 .32em; border-radius:.38em;
    background:#ffc94a; color:#111827 !important;
    font-weight:800; box-shadow:0 3px 0 #6b4e00;
    transform-origin:center;
    animation:child-name-pop .5s cubic-bezier(.2,.8,.2,1) both;
}
@keyframes child-name-pop {
    0% { opacity:.55; transform:translateY(.25em) scale(.88); }
    70% { opacity:1; transform:translateY(-.06em) scale(1.06); }
    100% { opacity:1; transform:translateY(0) scale(1); }
}
.action-card {
    padding:1.45rem 1.2rem; min-height:155px; border-radius:24px;
    border:2px solid #fff; text-align:center;
    background:linear-gradient(145deg,#fff 0%,#eff8ff 100%);
    box-shadow:0 8px 22px rgba(53,86,144,.11),inset 0 0 0 2px #cde5ff;
}
.action-card h3 { font-size:1.5rem !important; color:var(--blue) !important; margin-bottom:.4rem; }
.action-card p { font-size:1.05rem; color:var(--body) !important; }

/* Home cards are single, full-card buttons: one obvious tap and keyboard target. */
.st-key-home_learn_card button,
.st-key-home_quiz_card button,
.st-key-home_garden_card button {
    display:flex; width:100%; min-height:155px;
    align-items:center; justify-content:center;
    padding:1.25rem !important; white-space:normal;
    text-align:center; cursor:pointer;
    background:linear-gradient(145deg,#ffffff 0%,#eff8ff 100%) !important;
    color:var(--ink) !important;
    border:2px solid #64748b !important;
    border-radius:24px !important;
    box-shadow:0 8px 22px rgba(53,86,144,.11),inset 0 0 0 2px #cde5ff !important;
    transition:transform .18s ease,box-shadow .18s ease,background .18s ease;
}
.st-key-home_learn_card button:hover,
.st-key-home_quiz_card button:hover,
.st-key-home_garden_card button:hover {
    background:linear-gradient(145deg,#ffffff 0%,#e6f4ff 100%) !important;
    border-color:var(--blue) !important;
    transform:translateY(-4px) scale(1.015);
    box-shadow:0 14px 28px rgba(53,86,144,.18),inset 0 0 0 2px #cde5ff !important;
}
.st-key-home_learn_card button:active,
.st-key-home_quiz_card button:active,
.st-key-home_garden_card button:active {
    transform:scale(.985);
}
.st-key-home_learn_card button p,
.st-key-home_quiz_card button p,
.st-key-home_garden_card button p {
    color:var(--body) !important; font-family:'Nunito','Trebuchet MS',Arial,sans-serif !important;
    font-size:1rem !important;
    line-height:1.4; font-weight:500;
}
.st-key-home_learn_card button strong,
.st-key-home_quiz_card button strong,
.st-key-home_garden_card button strong {
    display:block; color:var(--blue) !important;
    font-family:'Baloo 2','Trebuchet MS',sans-serif !important;
    font-size:1.55rem; font-weight:800;
}
.st-key-home_learn_card { animation:card-rise .42s ease-out both; }
.st-key-home_quiz_card { animation:card-rise .42s ease-out .08s both; }
.st-key-home_garden_card { animation:card-rise .42s ease-out .16s both; }
@keyframes card-rise {
    from { opacity:.65; transform:translateY(8px); }
    to { opacity:1; transform:translateY(0); }
}

/* Visible keyboard focus and reduced-motion support. */
:where(button,input,textarea,select,a,[tabindex]):focus-visible {
    outline:3px solid var(--focus) !important; outline-offset:3px !important;
    box-shadow:0 0 0 2px var(--ink) !important;
}
@media (max-width:640px) {
    [data-testid="stMainBlockContainer"] { padding:.75rem .75rem 1.5rem; }

    /* Put home-page action cards in a single, readable column. */
    [data-testid="stHorizontalBlock"] {
        flex-direction:column !important;
        gap:.75rem !important;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        width:100% !important;
        min-width:100% !important;
        flex:1 1 100% !important;
    }

    .hero { padding:1.25rem 1rem; margin-bottom:1rem; border-radius:20px; }
    .hero h1 { font-size:clamp(1.6rem,7vw,2rem) !important; line-height:1.15; }
    .child-name { padding:0 .24em; }
    .hero p { font-size:1rem; line-height:1.45; }
    .action-card { min-height:auto; padding:1rem; border-radius:18px; }

    /* Full-width, easy-to-tap actions and fields on phones. */
    .stButton > button,
    [data-testid="stFormSubmitButton"] button {
        width:100%;
        min-height:48px;
        font-size:1.0625rem !important;
    }
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stSelectbox"] [role="combobox"] {
        min-height:48px;
        font-size:18px !important;
    }
    [data-testid="stExpander"] summary { min-height:48px; }
    p, li, [data-testid="stMarkdownContainer"] p {
        font-size:1.0625rem !important;
        line-height:1.45;
        font-weight:500;
    }
}
@media (prefers-reduced-motion:reduce) {
    *,*::before,*::after { scroll-behavior:auto !important; transition:none !important; animation:none !important; }
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=15, show_spinner=False)
def fetch_remote_lists(child_name: str = "") -> dict[str, str]:
    if API_URL:
        try:
            params = {"action": "get_lists"}
            if child_name:
                params["child_name"] = child_name
            resp = requests.get(API_URL, params=params, allow_redirects=True, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}


def save_remote_list(title: str, words: str, child_name: str) -> bool:
    if API_URL:
        try:
            resp = requests.post(
                API_URL, 
                json={"action": "save", "title": title, "words": words, "child_name": child_name}, 
                timeout=5
            )
            st.cache_data.clear()
            return resp.status_code == 200
        except Exception as e:
            st.error(f"Failed to sync save to database: {e}")
    return False


def delete_remote_list(title: str, child_name: str) -> bool:
    if API_URL:
        try:
            resp = requests.post(
                API_URL, 
                json={"action": "delete", "title": title, "child_name": child_name}, 
                timeout=5
            )
            st.cache_data.clear()
            return resp.status_code == 200
        except Exception as e:
            st.error(f"Failed to sync delete to database: {e}")
    return False


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


def sync_child_profiles(children: list[str]) -> None:
    if API_URL:
        try:
            requests.post(API_URL, json={"action": "save_profiles", "children": children}, timeout=5)
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Failed to sync learner profiles: {e}")


if "children" not in st.session_state:
    st.session_state.children = fetch_child_profiles()

if "active_child" not in st.session_state:
    st.session_state.active_child = st.session_state.children[0]

if "parent_unlocked" not in st.session_state:
    st.session_state.parent_unlocked = False


def rename_child_profile(old_name: str, new_name: str):
    if not new_name or new_name == old_name:
        return
    if old_name in st.session_state.children:
        idx = st.session_state.children.index(old_name)
        st.session_state.children[idx] = new_name
    
    st.session_state.active_child = new_name

    for key_prefix in ["active_week", "raw_words", "cached_analysis", "quiz_index", "quiz_score", "quiz_checked", "quiz_logged", "quiz_result", "mastered_words", "unfamiliar_words", "archived_lists"]:
        old_key = f"{key_prefix}_{old_name}"
        new_key = f"{key_prefix}_{new_name}"
        if old_key in st.session_state:
            st.session_state[new_key] = st.session_state.pop(old_key)

    sync_child_profiles(st.session_state.children)


with st.sidebar:
    st.subheader("👤 Who is practicing today?")
    
    selected_child = st.selectbox(
        "Select Learner:",
        options=st.session_state.children,
        index=st.session_state.children.index(st.session_state.active_child) if st.session_state.active_child in st.session_state.children else 0
    )
    if selected_child != st.session_state.active_child:
        st.session_state.active_child = selected_child
        st.rerun()

    active_child = st.session_state.active_child

    with st.expander("✏️ Edit Current Learner Name", expanded=False):
        edited_name = st.text_input("New Name:", value=active_child, key=f"rename_input_{active_child}")
        if st.button("Save New Name", type="primary", use_container_width=True):
            clean_rename = edited_name.strip()
            if clean_rename and clean_rename != active_child:
                rename_child_profile(active_child, clean_rename)
                st.success(f"Renamed to {clean_rename}!")
                st.rerun()

    with st.expander("➕ Add New Learner", expanded=False):
        new_child_name = st.text_input("Child's Name:", placeholder="e.g., Lucas", key="add_new_child_input")
        if st.button("Add Learner Profile", type="secondary", use_container_width=True):
            clean_name = new_child_name.strip()
            if clean_name and clean_name not in st.session_state.children:
                st.session_state.children.append(clean_name)
                st.session_state.active_child = clean_name
                sync_child_profiles(st.session_state.children)
                st.success(f"Added profile for {clean_name}!")
                st.rerun()

active_child = st.session_state.active_child
safe_active_child = escape(str(active_child))

st.markdown(f"""
<div class="hero">
    <h1>👋 Hi <span class="child-name">{safe_active_child}!</span> Welcome to Magic Spelling World! ✏️</h1>
    <p>Listen, practice handwriting, and master Chinese & English spelling today!</p>
</div>
""", unsafe_allow_html=True)

st.write(f"### 🚀 What would **{active_child}** like to do?")

col1, col2 = st.columns(2)

with col1:
    if st.button(
        "**📖 Learn Words**\n\nExplore meanings, pinyin, stroke orders & memory tricks!",
        key="home_learn_card",
        type="secondary",
        use_container_width=True,
        help=f"Open Learn Words for {active_child}",
    ):
        st.switch_page("pages/1_📖_Learn_Words.py")

with col2:
    if st.button(
        "**🎯 Dictation Quiz**\n\nListen to audio & test your handwriting!",
        key="home_quiz_card",
        type="secondary",
        use_container_width=True,
        help="Open Dictation Quiz",
    ):
        st.switch_page("pages/2_🎯_Dictation_Quiz.py")

if st.button(
    "**🌱 Word Garden**\n\nSee your stars and watch mastered words grow into flowers!",
    key="home_garden_card",
    type="secondary",
    use_container_width=True,
    help="Open your Word Garden",
):
    st.switch_page("pages/4_🌱_Word Garden.py")

st.divider()

PARENT_PIN = "6666"

with st.expander("🔒 Parent Area: Manage Spelling Lists (PIN Required)", expanded=False):
    st.caption("Grown-ups only! Enter PIN to add, update, or delete spelling lists.")

    if not st.session_state.parent_unlocked:
        entered_pin = st.text_input("Enter 4-digit Parent PIN:", type="password", key="pin_entry_field")
        if entered_pin == PARENT_PIN:
            st.session_state.parent_unlocked = True
            st.rerun()
        elif entered_pin != "":
            st.error("❌ Incorrect PIN. Please try again.")
    else:
        st.success("🔓 Unlocked!")
        if st.button("🔒 Lock Parent Area Now", type="secondary"):
            st.session_state.parent_unlocked = False
            st.rerun()

        st.write("---")
        
        st.write("### ➕ Add or Update List")
        target_child_for_list = st.selectbox(
            "Assign List To:",
            options=["All Learners"] + st.session_state.children,
            index=1 if active_child in st.session_state.children else 0,
            key="target_child_list_select"
        )
        new_week_title = st.text_input("Week Title / Name:", placeholder="e.g., Week 5: Animals & Weather")
        new_week_words = st.text_area("Spelling Words (one word per line):", height=120, placeholder="elephant\nrainbow\n事情\n生日")
        
        if st.button("💾 Save List to Google Sheets", type="primary"):
            title_clean = new_week_title.strip()
            words_clean = new_week_words.strip()
            if title_clean and words_clean:
                if save_remote_list(title_clean, words_clean, target_child_for_list):
                    st.success(f"Saved '{title_clean}' for {target_child_for_list}!")
                    st.session_state.parent_unlocked = False
                    st.rerun()
                else:
                    st.error("Could not save to Google Sheets. Please check your connection or Web App deployment.")
            else:
                st.warning("Please enter both a title and words before saving.")

        st.divider()

        st.write("### 🗑️ Delete an Existing List")
        active_child_lists = fetch_remote_lists(active_child)
        if active_child_lists:
            list_to_delete = st.selectbox(
                f"Select list to delete for {active_child}:",
                options=list(active_child_lists.keys()),
                key="delete_list_select"
            )
            if st.button(f"❌ Delete '{list_to_delete}'", type="secondary"):
                if delete_remote_list(list_to_delete, active_child):
                    st.success(f"Deleted '{list_to_delete}' successfully!")
                    st.session_state.parent_unlocked = False
                    st.rerun()
                else:
                    st.error("Failed to delete from Google Sheets.")
        else:
            st.caption(f"No spelling lists created for {active_child} yet.")
