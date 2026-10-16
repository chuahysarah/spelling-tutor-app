from __future__ import annotations

import json
import os
import re
import streamlit as st

st.set_page_config(page_title="Magic Spelling World ✏️", page_icon="⭐", layout="centered")

DATA_FILE = "weekly_lists.json"

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


def load_persistent_lists() -> dict[str, str]:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Default initial fallback list
    return {
        "Week 1: School & Friends": "beautiful\nfriend\n学校\n认真",
        "Week 2: Nature & Family": "mountain\nflower\n爸爸\n妈妈",
    }


def save_persistent_lists(data: dict[str, str]) -> None:
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Failed to save data: {e}")


def normalize_words(raw: str) -> list[str]:
    seen: set[str] = set()
    result = []
    for line in raw.replace("，", "\n").replace(",", "\n").splitlines():
        item = line.strip()
        if item and item.casefold() not in seen:
            seen.add(item.casefold())
            result.append(item)
    return result


# Load Permanent Archive from JSON file into Session State
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

# Sidebar: Parent API Key Configuration
with st.sidebar:
    st.subheader("👨‍👩‍👧 For Grown-Ups")
    api_key_input = st.text_input("Google Gemini API Key (optional)", type="password", value=st.session_state.get("api_key", ""))
    if api_key_input:
        st.session_state.api_key = api_key_input.strip()

# Child Section: Select Active Weekly List
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

# Parent Section: PIN Locked Area
PARENT_PIN = "6666"

with st.expander("🔒 Parent Area: Manage Spelling Lists (PIN Required)", expanded=False):
    st.caption("Grown-ups only! Enter PIN to unlock management controls.")
    entered_pin = st.text_input("Enter 4-digit Parent PIN:", type="password", key="parent_pin_input")

    if entered_pin == PARENT_PIN:
        st.success("🔓 Unlocked!")
        st.write("---")
        
        # 1. Add or Update List
        st.write("### ➕ Add or Update List")
        new_week_title = st.text_input("Week Title / Name:", placeholder="e.g., Week 3: Animals & Weather")
        new_week_words = st.text_area("Spelling Words (one word per line):", height=120, placeholder="elephant\nrainbow\n动物\n天气")
        
        if st.button("💾 Save Permanently to Archive", type="primary"):
            if new_week_title.strip() and new_week_words.strip():
                st.session_state.archived_lists[new_week_title.strip()] = new_week_words.strip()
                save_persistent_lists(st.session_state.archived_lists)  # Saves to weekly_lists.json!
                
                st.session_state.active_week = new_week_title.strip()
                st.session_state.raw_words = new_week_words.strip()
                st.session_state.quiz_words = normalize_words(new_week_words.strip())
                st.session_state.quiz_index = 0
                st.session_state.quiz_score = 0
                st.session_state.quiz_checked = False
                st.session_state.cached_analysis = {}
                st.success(f"🎉 Saved '{new_week_title}' permanently!")
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
                save_persistent_lists(st.session_state.archived_lists)  # Save deletion to JSON!
                st.success(f"Deleted '{list_to_delete}'!")
                
                if list_to_delete == st.session_state.active_week:
                    if st.session_state.archived_lists:
                        st.session_state.active_week = list(st.session_state.archived_lists.keys())[0]
                        st.session_state.raw_words = st.session_state.archived_lists[st.session_state.active_week]
                    else:
                        st.session_state.active_week = ""
                        st.session_state.raw_words = ""
                    st.session_state.cached_analysis = {}
                st.rerun()
        else:
            st.caption("No archived lists to delete.")
            
    elif entered_pin != "":
        st.error("❌ Incorrect PIN. Please try again.")

words = normalize_words(st.session_state.raw_words)
if words:
    st.success(f"✨ Currently loaded **{len(words)} word(s)** for {st.session_state.active_week}. Select '📖 Learn Words' or '🎯 Dictation Quiz' in the sidebar to begin!")
