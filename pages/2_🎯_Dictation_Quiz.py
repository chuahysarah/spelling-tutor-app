from __future__ import annotations

import datetime
import io
import json
import re
import requests
import streamlit as st
from gtts import gTTS
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="Dictation Quiz 🎯", page_icon="🎯", layout="centered")

API_URL = st.secrets.get("GSHEETS_API_URL", "").strip()

st.title("🎯 Spelling & Chinese Dictation Quiz")


def log_completed_quiz(week_title: str, score: int, total_words: int, mastered: set, unfamiliar: set):
    """Sends completed quiz results live to Google Sheets database."""
    if API_URL:
        try:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            payload = {
                "action": "log_quiz",
                "timestamp": now_str,
                "week_title": week_title,
                "score": score,
                "total_words": total_words,
                "mastered": ", ".join(mastered) if mastered else "None",
                "unfamiliar": ", ".join(unfamiliar) if unfamiliar else "None"
            }
            requests.post(API_URL, json=payload, timeout=5)
        except Exception as e:
            st.error(f"Failed to log quiz attempt: {e}")


def speak_text(text: str):
    """Generates audio for English or Chinese spelling words."""
    try:
        lang = 'zh-cn' if re.search(r'[\u4e00-\u9fff]', text) else 'en'
        tts = gTTS(text=text, lang=lang, slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp, format="audio/mp3", autoplay=True)
    except Exception:
        st.warning("Audio playback failed.")


def normalize_words(raw: str) -> list[str]:
    seen: set[str] = set()
    result = []
    for line in raw.replace("，", "\n").replace(",", "\n").splitlines():
        item = line.strip()
        if item and item.casefold() not in seen:
            seen.add(item.casefold())
            result.append(item)
    return result


# Verify Active Week & Words
active_week = st.session_state.get("active_week", "")
raw_words = st.session_state.get("raw_words", "")
quiz_words = normalize_words(raw_words)

if not quiz_words:
    st.warning("⚠️ No words found in the active list. Please select a weekly list on the home page first!")
    st.stop()

# Initialize Quiz State
if "quiz_index" not in st.session_state:
    st.session_state.quiz_index = 0
if "quiz_score" not in st.session_state:
    st.session_state.quiz_score = 0
if "quiz_checked" not in st.session_state:
    st.session_state.quiz_checked = False
if "quiz_logged" not in st.session_state:
    st.session_state.quiz_logged = False
if "mastered_words" not in st.session_state:
    st.session_state.mastered_words = set()
if "unfamiliar_words" not in st.session_state:
    st.session_state.unfamiliar_words = set()

total_q = len(quiz_words)
current_idx = st.session_state.quiz_index

# QUIZ COMPLETED SCREEN
if current_idx >= total_q:
    st.balloons()
    st.success("🎉 Quiz Completed! Outstanding effort!")
    
    final_score = st.session_state.quiz_score
    st.metric(label="Final Score", value=f"{final_score} / {total_q}")

    if not st.session_state.quiz_logged:
        log_completed_quiz(
            week_title=active_week,
            score=final_score,
            total_words=total_q,
            mastered=st.session_state.mastered_words,
            unfamiliar=st.session_state.unfamiliar_words
        )
        st.session_state.quiz_logged = True
        st.info("✅ Your score and practice details have been saved to the Parent History!")

    if st.button("🔄 Restart Quiz", type="primary"):
        st.session_state.quiz_index = 0
        st.session_state.quiz_score = 0
        st.session_state.quiz_checked = False
        st.session_state.quiz_logged = False
        st.rerun()
    st.stop()

# ACTIVE QUIZ QUESTION SCREEN
target_word = quiz_words[current_idx]
is_chinese = bool(re.search(r'[\u4e00-\u9fff]', target_word))

st.progress((current_idx) / total_q)
st.caption(f"Question {current_idx + 1} of {total_q} — **{active_week}**")

st.write("### 🔊 Listen and write down the word:")
if st.button("🔊 Play Word Sound", type="secondary"):
    speak_text(target_word)

st.write("---")

# HANDWRITING PAD SECTION (Drawing canvas for both Chinese & English)
st.subheader("✏️ Handwriting Practice Pad")
st.caption("Use your touchscreen, finger, or mouse to write your answer directly on the canvas below:")

canvas_result = st_canvas(
    fill_color="rgba(255, 255, 255, 0)",
    stroke_width=4,
    stroke_color="#1e293b",
    background_color="#f8fafc",
    height=220,
    width=340,
    drawing_mode="freedraw",
    key=f"canvas_{current_idx}"
)

# Text Verification Input
user_answer = st.text_input("Type or verify your answer here for auto-grading:", key=f"quiz_ans_{current_idx}")

# Reference Check Box (Helpful for Chinese Strokes & Character Reference)
with st.expander("💡 Need a Hint / Reference Check?"):
    if is_chinese:
        st.write(f"**Target Character:** {target_word}")
        st.caption("Practice writing the strokes on the canvas above!")
    else:
        st.write(f"**Hint / First Letter:** {target_word[0].upper()}...")

col1, col2 = st.columns(2)

with col1:
    if st.button("✅ Submit & Grade Answer", type="primary"):
        clean_user = user_answer.strip().casefold()
        clean_target = target_word.strip().casefold()

        if clean_user == clean_target:
            st.success(f"🌟 Correct! Awesome job: **{target_word}**")
            st.session_state.quiz_score += 1
            st.session_state.mastered_words.add(target_word)
        else:
            st.error(f"❌ Almost! The correct word is: **{target_word}**")
            st.session_state.unfamiliar_words.add(target_word)

        st.session_state.quiz_checked = True

with col2:
    if st.session_state.quiz_checked:
        if st.button("➡️ Next Word", type="secondary"):
            st.session_state.quiz_index += 1
            st.session_state.quiz_checked = False
            st.rerun()
