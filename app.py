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


if "raw_words" not in st.session_state:
    st.session_state.raw_words = ""
if "mastered_words" not in st.session_state:
    st.session_state.mastered_words = set()
if "unfamiliar_words" not in st.session_state:
    st.session_state.unfamiliar_words = set()

with st.sidebar:
    st.subheader("👨‍👩‍👧 For Grown-Ups")
    api_key_input = st.text_input("Google Gemini API Key (optional)", type="password", value=st.session_state.get("api_key", ""))
    if api_key_input:
        st.session_state.api_key = api_key_input.strip()

st.subheader("📝 Step 1: Add your weekly words!")
with st.form("word_list_form"):
    raw = st.text_area("Type your list here (one word per line):", value=st.session_state.raw_words, height=160, placeholder="beautiful\nfriend\n学校\n认真")
    submitted = st.form_submit_button("🚀 Save Word List", type="primary")

if submitted:
    st.session_state.raw_words = raw
    st.session_state.quiz_words = normalize_words(raw)
    st.session_state.quiz_index = 0
    st.session_state.quiz_score = 0
    st.session_state.quiz_checked = False
    st.session_state.mastered_words = set()
    st.session_state.unfamiliar_words = set()
    # Reset cached AI analysis on new list submission
    st.session_state.cached_analysis = {}
    st.success("🎉 Words saved! Select '📖 Learn Words' or '🎯 Dictation Quiz' from the sidebar menu to begin!")

words = normalize_words(st.session_state.raw_words)
if words:
    st.info(f"✨ Currently practicing {len(words)} word(s). Use the sidebar navigation on the left to start!")
