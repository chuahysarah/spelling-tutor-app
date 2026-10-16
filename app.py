from __future__ import annotations

import json
import os
import re
import requests
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Magic Spelling World ✏️", page_icon="⭐", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Fredoka', cursive, sans-serif; }
.hero {
    padding: 1.5rem; 
    border-radius: 24px; 
    background: linear-gradient(135deg, #fef9c3 0%, #e0f2fe 100%); 
    border: 3px solid #fde047;
    text-align: center;
    margin-bottom: 1.5rem;
}
.hero h1 { color: #0284c7; margin: 0; }
</style>
<div class="hero">
    <h1>🌟 Magic Spelling World! ✏️</h1>
    <div>Listen, practice writing, and become a spelling star!</div>
</div>
""", unsafe_allow_html=True)


# Initialize Google Sheets Connection safely
def load_persistent_lists() -> dict[str, str]:
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=0)
        result = {}
        for _, row in df.iterrows():
            title = str(row["week_title"]).strip()
            words = str(row["words"]).replace("\\n", "\n").strip()
            if title and words:
                result[title] = words
        if result:
            return result
    except Exception:
        pass
    
    return {
        "Week 1: School & Friends": "beautiful\nfriend\n学校\n认真",
        "Week 2: Nature & Family": "mountain\nflower\n爸爸\n妈妈",
    }


def save_persistent_lists(data: dict[str, str]) -> None:
    try:
        import pandas as pd
        conn = st.connection("gsheets", type=GSheetsConnection)
        rows = [{"week_title": k, "words": v.replace("\n", "\\n")} for k, v in data.items()]
        df = pd.DataFrame(rows)
        conn.update(data=df)
        st.success("Synced live to database!")
    except Exception as e:
        st.warning(f"Saved locally to active session.")


def normalize_words(raw: str) -> list[str]:
    seen: set[str] = set()
    result = []
    for line in raw.replace("，", "\n").replace(",", "\n").splitlines():
        item = line.strip()
        if item and item.casefold() not in seen:
            seen.add(item.casefold())
            result.append(item)
    return result


# Initialize Persistent Archive in Session State
if "archived_lists" not in st.session_state:
    st.session_state.archived_lists = load_persistent_lists()

if "active_week" not in st.session_state or st.session_state.active_week not in st.session_state.archived_lists:
    if st.session_state.archived_lists:
        st.session_state.active_week = list(st.session_state.archived_lists.keys())[0]
    else:
        st.session_state.active_week = ""

if "raw_words" not in st.session_state:
    st.session_state.raw_words = st.session_state.archived_lists.get(st.session_state.active_week, "")

if "mastered_words" not in st.session_state:
    st.session_state.mastered_words = set()
if "unfamiliar_words" not in st.session_state:
    st.session_state.unfamiliar_words = set()

if "parent_unlocked" not in st.session_state:
    st.session_state.parent_unlocked = False

# Sidebar Configuration
with st.sidebar:
    st.subheader("👨‍👩‍👧 For Grown-Ups")
    api_key_input = st.text_input("Google Gemini API Key (optional)", type="password", value=st.session_state.get("api_key", ""))
    if api_key_input:
        st.session_state.api_key = api_key_input.strip()

# Child Section
st.subheader("🎒 Step 1: Select Your Week!")

if st.session_state.archived_lists:
    options_list = list(st.session_state.archived_lists.keys())
    curr_index = options_list.index(st.session_state.active_week) if st.session_state.active_week in options_list else 0
    selected_week = st.selectbox(
        "Choose which week you want to practice today:",
        options=options_list,
        index=curr_index
    )

    if selected_week != st.session_state.active_week:
        st.session_state.active_week = selected_week
        st.session_state.raw_words = st.session_state.archived_lists[selected_week]
        st.session_state.quiz_words = normalize_words(st.session_state.raw_words)
        st.session_state.quiz_index = 0
        st.session_state.quiz_score = 0
        st.session_state.quiz_checked = False
        st.session_state.cached_analysis = {}
        st.rerun()

    st.info(f"📍 Active Practice List: **{st.session_state.active_week}**")
else:
    st.warning("No spelling lists available. Unlock the Parent Area below to add a new list!")

# Parent Section: Clean Safe Authentication Flow
PARENT_PIN = "6666"

with st.expander("🔒 Parent Area: Manage Spelling Lists (PIN Required)", expanded=False):
    st.caption("Grown-ups only! Enter PIN to unlock management controls.")

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
        
        # 1. Add or Update List
        st.write("### ➕ Add or Update List")
        new_week_title = st.text_input("Week Title / Name:", placeholder="e.g., Week 3: Animals & Weather")
        new_week_words = st.text_area("Spelling Words (one word per line):", height=120, placeholder="elephant\nrainbow\n动物\n天气")
        
        if st.button("💾 Save List", type="primary"):
            title_clean = new_week_title.strip()
            words_clean = new_week_words.strip()
            if title_clean and words_clean:
                st.session_state.archived_lists[title_clean] = words_clean
                save_persistent_lists(st.session_state.archived_lists)
                
                st.session_state.active_week = title_clean
                st.session_state.raw_words = words_clean
                st.session_state.quiz_words = normalize_words(words_clean)
                st.session_state.quiz_index = 0
                st.session_state.quiz_score = 0
                st.session_state.quiz_checked = False
                st.session_state.cached_analysis = {}

                # Safely re-lock panel upon saving
                st.session_state.parent_unlocked = False
                st.rerun()
            else:
                st.warning("Please enter both a title and words before saving.")

        st.divider()

        # 2. Delete an Existing List
        st.write("### 🗑️ Delete an Existing List")
        if st.session_state.archived_lists:
            list_to_delete = st.selectbox(
                "Select list to delete:",
                options=list(st.session_state.archived_lists.keys()),
                key="delete_list_select"
            )
            if st.button(f"❌ Delete '{list_to_delete}'", type="secondary"):
                del st.session_state.archived_lists[list_to_delete]
                save_persistent_lists(st.session_state.archived_lists)
                
                if list_to_delete == st.session_state.active_week:
                    if st.session_state.archived_lists:
                        st.session_state.active_week = list(st.session_state.archived_lists.keys())[0]
                        st.session_state.raw_words = st.session_state.archived_lists[st.session_state.active_week]
                    else:
                        st.session_state.active_week = ""
                        st.session_state.raw_words = ""
                    st.session_state.cached_analysis = {}

                st.session_state.parent_unlocked = False
                st.rerun()
        else:
            st.caption("No archived lists to delete.")

words = normalize_words(st.session_state.raw_words)
if words:
    st.success(f"✨ Currently loaded **{len(words)} word(s)** for {st.session_state.active_week}. Select '📖 Learn Words' or '🎯 Dictation Quiz' in the sidebar to begin!")
