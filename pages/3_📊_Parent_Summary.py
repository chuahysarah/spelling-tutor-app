from __future__ import annotations

import json
import requests
import streamlit as st

st.set_page_config(page_title="Parent Dashboard 📊", page_icon="📊", layout="centered")

API_URL = st.secrets.get("GSHEETS_API_URL", "").strip()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600;700&display=swap');

html, body, [class*="css"], button, input, select {
    font-family: 'Fredoka', cursive, sans-serif !important;
    font-size: 1.15rem;
}

h1 { font-size: 2.6rem !important; color: #0284c7 !important; }
h2 { font-size: 2.1rem !important; color: #0369a1 !important; }
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
