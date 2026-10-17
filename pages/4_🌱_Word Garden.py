from __future__ import annotations

import html
import requests
import streamlit as st

st.set_page_config(
    page_title="Word Garden 🌱",
    page_icon="🌱",
    layout="centered",
    initial_sidebar_state="expanded",
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
.garden-banner {
    padding: 1.3rem 1.5rem;
    margin: .5rem 0 1.2rem;
    border: 2px solid #c7ead5;
    border-radius: 22px;
    background: linear-gradient(120deg, #e8f8df, #e5f4ff 55%, #fff1c9);
    text-align: center;
}
.garden-banner p { margin: .25rem 0 0; color: #40564a; }
.garden-card {
    padding: 1.2rem;
    border: 2px solid #d8efdc;
    border-radius: 22px;
    background: linear-gradient(160deg, #f7fff0, #effaf6);
    text-align: center;
}
.garden-scene {
    min-height: 230px;
    padding: 1.2rem 1rem .75rem;
    border: 3px solid #b8dfac;
    border-radius: 26px;
    background: linear-gradient(180deg, #dff3ff 0%, #eff9ff 45%, #d7efb4 46%, #b8dd8d 100%);
    box-shadow: inset 0 -12px 0 rgba(101, 158, 73, .12);
    text-align: center;
}
.garden-sun { font-size: 2.6rem; }
.garden-flowers { min-height: 100px; padding: .4rem 0; font-size: 2.6rem; line-height: 1.65; }
.garden-ground { margin-top: .3rem; color: #46683d; font-weight: 700; }
.small-note { color: #566477; font-size: .95rem; }

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


@st.cache_data(ttl=15, show_spinner=False)
def fetch_child_profiles() -> list[str]:
    if API_URL:
        try:
            response = requests.get(API_URL, params={"action": "get_profiles"}, timeout=5)
            if response.ok:
                profiles = response.json()
                if isinstance(profiles, list) and profiles:
                    return [str(name) for name in profiles if str(name).strip()]
        except (requests.RequestException, ValueError):
            pass
    return ["Alex", "Emma"]


@st.cache_data(ttl=15, show_spinner=False)
def fetch_practice_history() -> list[dict]:
    if API_URL:
        try:
            response = requests.get(API_URL, params={"action": "get_history"}, timeout=5)
            if response.ok:
                history = response.json()
                if isinstance(history, list):
                    return [row for row in history if isinstance(row, dict)]
        except (requests.RequestException, ValueError):
            pass
    return []


def as_int(value: object) -> int:
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError, OverflowError):
        return 0


def mastered_words_from(value: object) -> list[str]:
    """Parse the comma-separated `mastered` value written by the quiz page."""
    if not isinstance(value, str) or value.strip().casefold() in {"", "none", "n/a"}:
        return []
    # Quiz history currently stores English/Chinese words separated by commas.
    return [word.strip() for word in value.replace("，", ",").split(",") if word.strip()]


profiles = fetch_child_profiles()
if "active_child" not in st.session_state or st.session_state.active_child not in profiles:
    st.session_state.active_child = profiles[0]

with st.sidebar:
    st.subheader("👤 Practicing Learner")
    selected_child = st.selectbox(
        "Current Child:",
        options=profiles,
        index=profiles.index(st.session_state.active_child),
        key="garden_active_child",
    )
    st.session_state.active_child = selected_child

child = st.session_state.active_child
st.title(f"🌱 {child}’s Word Garden")
st.markdown(
    '<div class="garden-banner"><strong>Every word you practice helps your garden grow!</strong>'
    '<p>Keep learning, collect sunshine stars, and watch your special words bloom.</p></div>',
    unsafe_allow_html=True,
)

history = fetch_practice_history()
child_history = [
    row for row in history
    if str(row.get("child_name", "")).strip().casefold() == child.casefold()
]

# Stars reward correct answers across recorded quizzes. A word is planted only once,
# even if the learner practices it again later.
stars_earned = sum(as_int(row.get("score", 0)) for row in child_history)
mastered_words = {
    word.casefold(): word
    for row in child_history
    for word in mastered_words_from(row.get("mastered", ""))
}
unique_words = len(mastered_words)
plant_count = unique_words // 3
next_plant_in = 3 - (unique_words % 3)

flower_types = ["🌼", "🌷", "🌻", "🌸", "🌺", "🪻", "🌹", "🌼", "🌷", "🌻", "🌸", "🌺"]
flowers_to_show = min(plant_count, len(flower_types))
flowers = " ".join(flower_types[:flowers_to_show]) if flowers_to_show else "🌱"
if plant_count > len(flower_types):
    flowers += f"  +{plant_count - len(flower_types)} more blooms"

st.markdown(
    f'<div class="garden-scene"><div class="garden-sun">☀️</div>'
    f'<div class="garden-flowers">{flowers}</div>'
    f'<div class="garden-ground">{html.escape(child)}’s growing garden</div></div>',
    unsafe_allow_html=True,
)

st.write("")
col_stars, col_words, col_plants = st.columns(3)
with col_stars:
    st.metric("☀️ Sunshine Stars", stars_earned)
with col_words:
    st.metric("📚 Words Mastered", unique_words)
with col_plants:
    st.metric("🌷 Flowers Grown", plant_count)

if not API_URL:
    st.info("Practice history storage is not connected. Your garden will grow once the app’s history service is configured.")
elif not child_history:
    st.info("Finish a dictation quiz to earn your first sunshine stars and help your garden grow!")
else:
    if unique_words % 3 == 0 and unique_words > 0:
        st.success(f"🌟 Lovely work, {child}! You’ve grown a new flower.")
    else:
        st.info(f"🌼 Master {next_plant_in} more unique word{'s' if next_plant_in != 1 else ''} to grow your next flower.")

with st.expander("How do garden rewards work?", expanded=False):
    st.markdown(
        "- Earn **1 sunshine star** for each correct answer recorded in a completed dictation quiz.\n"
        "- Master **3 different words** to grow a flower. Repeating a mastered word still helps you practice, "
        "but does not plant a duplicate.\n"
        "- Your garden is calculated from the app’s saved practice history, so it follows the selected learner."
    )

with st.expander("Words in my garden", expanded=False):
    if mastered_words:
        st.write(", ".join(sorted(mastered_words.values(), key=str.casefold)))
    else:
        st.caption("Your first flower starts with your first mastered word!")

st.caption("Garden rewards are based on completed quiz history; no extra account or data storage is needed.")
