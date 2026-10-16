from __future__ import annotations

import re
import streamlit as st

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


def normalize_words(raw: str) -> list[str]:
    seen: set[str] = set()
    result = []
    for line in raw.replace("，", "\n").replace(",", "\n").splitlines():
        item = line.strip()
        if item and item.casefold() not in seen:
            seen.add(item.casefold())
            result.append(item)
    return result


# Initialize Persistent Weekly Archive in Session State
if "archived_lists" not in st.session_state:
    st.session_state.archived_lists = {
        "Week 1: School & Friends": "beautiful\nfriend\n学校\n认真",
        "Week 2: Nature & Family": "mountain\nflower\n爸爸\n妈妈",
    }

if "active_week" not in st.session_state:
    st.session_state.active_week = "Week 1: School & Friends"

if "raw_words" not in st.session_state:
    st.session_state.raw_words = st.session_state.archived_lists[st.session_state.active_week]

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
selected_week = st.selectbox(
    "Choose which week you want to practice today:",
    options=list(st.session_state.archived_lists.keys()),
    index=list(st.session_state.archived_lists.keys()).index(st.session_state.active_week)
)

# Load selected weekly list into active practice session
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

# Parent Section: Pre-populate or Add New Weekly Lists
with st.expander("🛠️ Parent Area: Add or Edit Weekly Spelling Lists", expanded=False):
    st.write("Pre-populate weekly lists here so your child can easily pick their week above!")
    new_week_title = st.text_input("Week Title / Name:", placeholder="e.g., Week 3: Animals & Weather")
    new_week_words = st.text_area("Spelling Words (one word per line):", height=120, placeholder="elephant\nrainbow\n动物\n天气")
    
    if st.button("💾 Save to Weekly Archive", type="primary"):
        if new_week_title.strip() and new_week_words.strip():
            st.session_state.archived_lists[new_week_title.strip()] = new_week_words.strip()
            st.session_state.active_week = new_week_title.strip()
            st.session_state.raw_words = new_week_words.strip()
            st.session_state.quiz_words = normalize_words(new_week_words.strip())
            st.session_state.quiz_index = 0
            st.session_state.quiz_score = 0
            st.session_state.quiz_checked = False
            st.session_state.cached_analysis = {}
            st.success(f"🎉 Saved '{new_week_title}' to the archive and set as active list!")
            st.rerun()
        else:
            st.warning("Please provide both a title and word list before saving.")

words = normalize_words(st.session_state.raw_words)
if words:
    st.success(f"✨ Currently loaded **{len(words)} word(s)** for {st.session_state.active_week}. Select '📖 Learn Words' or '🎯 Dictation Quiz' in the sidebar to begin!")
