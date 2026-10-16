from __future__ import annotations

import base64
import datetime
import io
import json
import re
import requests
import numpy as np
import streamlit as st
from gtts import gTTS
from PIL import Image
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="Dictation Quiz 🎯", page_icon="🎯", layout="centered")

API_URL = st.secrets.get("GSHEETS_API_URL", "").strip()
GEMINI_API_KEY = st.session_state.get("api_key", "") or st.secrets.get("GEMINI_API_KEY", "")

st.title("🎯 Spelling & Chinese Dictation Quiz")


def log_completed_quiz(week_title: str, score: int, total_words: int, mastered: set, unfamiliar: set):
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
    try:
        lang = 'zh-cn' if re.search(r'[\u4e00-\u9fff]', text) else 'en'
        tts = gTTS(text=text, lang=lang, slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp, format="audio/mp3", autoplay=True)
    except Exception:
        st.warning("Audio playback failed.")


def grade_handwriting_with_gemini(image_data, target_char: str, api_key: str) -> tuple[bool, str]:
    """Sends handwritten canvas drawing to Gemini AI for vision auto-grading."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        img = Image.fromarray(image_data.astype('uint8'), 'RGBA').convert('RGB')
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        prompt = (
            f"You are evaluating a child's handwritten Chinese character. "
            f"The intended target character is '{target_char}'. "
            f"Analyze the image strokes and respond strictly in valid JSON format with two keys: "
            f"'is_correct' (boolean: true or false) and 'feedback' (string: short encouraging feedback in English)."
        )

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_str}}
                ]
            }]
        }

        resp = requests.post(url, json=payload, timeout=8)
        if resp.status_code == 200:
            res_json = resp.json()
            text_resp = res_json['candidates'][0]['content']['parts'][0]['text']
            match = re.search(r'\{.*\}', text_resp, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                return parsed.get("is_correct", False), parsed.get("feedback", "Evaluated!")
    except Exception as e:
        pass
    return False, "Could not evaluate handwriting automatically."


def normalize_words(raw: str) -> list[str]:
    seen: set[str] = set()
    result = []
    for line in raw.replace("，", "\n").replace(",", "\n").splitlines():
        item = line.strip()
        if item and item.casefold() not in seen:
            seen.add(item.casefold())
            result.append(item)
    return result


active_week = st.session_state.get("active_week", "")
raw_words = st.session_state.get("raw_words", "")
quiz_words = normalize_words(raw_words)

if not quiz_words:
    st.warning("⚠️ No words found in the active list. Please select a weekly list on the home page first!")
    st.stop()

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

# Quiz Completion Screen
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

target_word = quiz_words[current_idx]
is_chinese = bool(re.search(r'[\u4e00-\u9fff]', target_word))

st.progress((current_idx) / total_q)
st.caption(f"Question {current_idx + 1} of {total_q} — **{active_week}**")

st.write("### 🔊 Listen and write down the word:")
if st.button("🔊 Play Word Sound", type="secondary"):
    speak_text(target_word)

st.write("---")

# Dedicated Drawing Canvas
st.subheader("✏️ Handwriting Practice Pad")
st.caption("Write your answer using your finger, stylus, or mouse in the box below:")

canvas_result = st_canvas(
    fill_color="rgba(255, 255, 255, 0)",
    stroke_width=5,
    stroke_color="#000000",
    background_color="#ffffff",
    height=260,
    width=340,
    drawing_mode="freedraw",
    key=f"canvas_{current_idx}"
)

# Render text input ONLY for English spelling lists
if not is_chinese:
    user_answer = st.text_input("Type your spelling answer here:", key=f"quiz_ans_{current_idx}")

col1, col2 = st.columns(2)

with col1:
    if st.button("✅ Grade Handwriting", type="primary"):
        if is_chinese:
            img_data = getattr(canvas_result, "image_data", None)
            
            # Robust stroke verification check across channels
            has_strokes = False
            if img_data is not None and isinstance(img_data, np.ndarray) and img_data.size > 0:
                # Check for drawn stroke presence via alpha channel or RGB variance
                has_alpha_strokes = np.any(img_data[:, :, 3] > 0)
                has_rgb_strokes = np.any(img_data[:, :, :3] < 200)
                has_strokes = has_alpha_strokes or has_rgb_strokes

            if not has_strokes and img_data is None:
                st.warning("✏️ Please write the character on the practice pad before grading!")
            elif GEMINI_API_KEY and img_data is not None:
                with st.spinner("Analyzing Chinese handwriting..."):
                    is_correct, feedback = grade_handwriting_with_gemini(
                        img_data, target_word, GEMINI_API_KEY
                    )
                    if is_correct:
                        st.success(f"🌟 Correct! Awesome handwriting: **{target_word}**")
                        st.write(f"💬 {feedback}")
                        st.session_state.quiz_score += 1
                        st.session_state.mastered_words.add(target_word)
                    else:
                        st.error(f"❌ Correct Character: **{target_word}**")
                        st.write(f"💬 {feedback}")
                        st.session_state.unfamiliar_words.add(target_word)
                    st.session_state.quiz_checked = True
            else:
                st.write(f"📖 Target Character: **{target_word}**")
                st.info("Please verify GEMINI_API_KEY is configured in Secrets for automatic vision grading!")
                st.session_state.quiz_checked = True
        else:
            clean_user = user_answer.strip().casefold() if 'user_answer' in locals() else ""
            clean_target = target_word.strip().casefold()
            if clean_user == clean_target:
                st.success(f"🌟 Correct! Awesome job: **{target_word}**")
                st.session_state.quiz_score += 1
                st.session_state.mastered_words.add(target_word)
            else:
                st.error(f"❌ Correct Spelling: **{target_word}**")
                st.session_state.unfamiliar_words.add(target_word)

            st.session_state.quiz_checked = True

with col2:
    if st.session_state.quiz_checked:
        if st.button("➡️ Next Word", type="secondary"):
            st.session_state.quiz_index += 1
            st.session_state.quiz_checked = False
            st.rerun()
