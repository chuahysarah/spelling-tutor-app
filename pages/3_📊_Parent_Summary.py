from __future__ import annotations

import json
import requests
import streamlit as st

st.set_page_config(page_title="Parent Dashboard 📊", page_icon="📊", layout="centered")

API_URL = st.secrets.get("GSHEETS_API_URL", "").strip()

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


st.subheader("🌟 Current Session Overview")
col1, col2 = st.columns(2)

mastered = st.session_state.get("mastered_words", set())
unfamiliar = st.session_state.get("unfamiliar_words", set())

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

st.subheader("📜 All Past Practice Attempts")

history = fetch_practice_history()

if history:
    for attempt in reversed(history):
        with st.expander(f"🗓️ {attempt.get('timestamp', 'N/A')} — {attempt.get('week_title', 'Spelling Practice')} (Score: {attempt.get('score')}/{attempt.get('total_words')})"):
            st.write(f"🎯 **Score:** {attempt.get('score')} / {attempt.get('total_words')}")
            st.write(f"✅ **Mastered Words:** {attempt.get('mastered', 'None')}")
            st.write(f"💡 **Needs Practice Words:** {attempt.get('unfamiliar', 'None')}")
else:
    st.info("No past practice logs found in database. Complete a quiz to start building practice history!")

if st.button("🔒 Lock Dashboard", type="secondary"):
    st.session_state.parent_dashboard_unlocked = False
    st.rerun()
