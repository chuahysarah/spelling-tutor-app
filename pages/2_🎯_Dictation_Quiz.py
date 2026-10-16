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


def get_gemini_key() -> str:
    """Prioritizes Streamlit Cloud Secrets to prevent old state overrides."""
    key = ""
    if "GEMINI_API_KEY" in st.secrets:
        key = str(st.secrets["GEMINI_API_KEY"])
    elif "gemini_api_key" in st.secrets:
        key = str(st.secrets["gemini_api_key"])
    elif st.session_state.get("api_key"):
        key = str(st.session_state.get("api_key"))
    
    return key.strip().strip("'").strip('"')


GEMINI_API_KEY = get_gemini_key()


def fetch_available_lists() -> dict[str, str]:
    if "archived_lists" in st.session_state and st.session_state.archived_lists:
        return st.session_state.archived_lists

    if API_URL:
        try:
            resp = requests.get(f"{API_URL}?action=get_lists", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and data:
                    st.session_state.archived_lists = data
                    return data
        except Exception:
            pass
    return {}


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
    """Sends handwritten drawing to Gemini 1.5 Flash using the v1 endpoint with header authentication."""
    try:
        clean_key = api_key.strip().strip("'").strip('"')
        
        # Target the stable v1 endpoint directly
        url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
        
        if isinstance(image_data, np.ndarray):
            img = Image.fromarray(image_data.astype('uint8'), 'RGBA').convert('RGB')
        else:
            img = image_data.convert('RGB')

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

        # Send authentication strictly in the header to avoid 401 URL collisions
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": clean_key
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=12)

        if resp.status_code == 200:
            res_json = resp.json()
            text_resp = res_json['candidates'][0]['content']['parts'][0]['text']
            match = re.search(r'\{.*\}', text_resp, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                return parsed.get("is_correct", False), parsed.get("feedback", "Evaluated successfully!")
            return True, "Handwriting evaluated!"
        else:
            return False, f"API Error ({resp.status_code}): {resp.text}"
    except Exception as e:
        return False, f"Error calling Gemini Vision API: {e}"


def normalize_words(raw: str) -> list[str]:
    seen: set[str] = set()
    result = []
    for line in raw.replace("，", "\n").replace(",", "\n").splitlines():
        item = line.strip()
        if item and item.casefold() not in seen:
            seen.add(item.casefold())
            result.append(item)
    return result


def reset_quiz_state():
    st.session_state.quiz_index = 0
    st.session_state.quiz_score = 0
    st.session_state.quiz_checked = False
    st.session_state.quiz_logged = False
    st.session_state.mastered_words = set()
    st.session_state.unfamiliar_words = set()


st.title("🎯 Spelling & Chinese Dictation Quiz")

available_lists = fetch_available_lists()
list_titles = list(available_lists.keys())

if not list_titles:
    st.warning("⚠️ No spelling lists available. Please create a list on the home page first!")
    st.stop()

current_active = st.session_state.get("active_week", "")
if current_active not in list_titles and list_titles:
    st.session_state.active_week = list_titles[0]
    st.session_state.raw_words = available_lists[list_titles[0]]
    reset_quiz_state()

default_idx = list_titles.index(st.session_state.active_week) if st.session_state.active_week in list_titles else 0

selected_list_title = st.selectbox(
    "📋 Select List to Dictate:",
    options=list_titles,
    index=default_idx,
    help="Choose the weekly list you want to practice now."
)

if selected_list_title != st.session_state.get("active_week"):
    st.session_state.active_week = selected_list_title
    st.session_state.raw_words = available_lists[selected_list_title]
    reset_quiz_state()
    st.rerun()

quiz_words = normalize_words(st.session_state.get("raw_words", ""))

if not quiz_words:
    st.warning("⚠️ No words found in the selected list. Please choose a different list above!")
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
            week_title=selected_list_title,
            score=final_score,
            total_words=total_q,
            mastered=st.session_state.mastered_words,
            unfamiliar=st.session_state.unfamiliar_words
        )
        st.session_state.quiz_logged = True
        st.info("✅ Your score and practice details have been saved to the Parent History!")

    if st.button("🔄 Restart Quiz", type="primary"):
        reset_quiz_state()
        st.rerun()
    st.stop()

target_word = quiz_words[current_idx]
is_chinese = bool(re.search(r'[\u4e00-\u9fff]', target_word))

st.progress((current_idx) / total_q)
st.caption(f"Question {current_idx + 1} of {total_q} — **{selected_list_title}**")

st.write("### 🔊 Listen and write down the word:")
if st.button("🔊 Play Word Sound", type="secondary"):
    speak_text(target_word)

st.write("---")

st.subheader("✏️ Handwriting Practice Pad")
st.caption("Write your answer using your finger, stylus, or mouse in the box below:")

canvas_result = st_canvas(
    fill_color="rgba(255, 255, 255, 0)",
    stroke_width=6,
    stroke_color="#000000",
    background_color="#ffffff",
    height=260,
    width=340,
    drawing_mode="freedraw",
    update_streamlit=True,
    return_image_data=True,
    key=f"canvas_{selected_list_title}_{current_idx}"
)

if not is_chinese:
    user_answer = st.text_input("Type your spelling answer here:", key=f"quiz_ans_{selected_list_title}_{current_idx}")

col1, col2 = st.columns(2)

with col1:
    if st.button("✅ Grade Answer", type="primary"):
        if is_chinese:
            if not GEMINI_API_KEY:
                st.error("❌ `GEMINI_API_KEY` is missing from Streamlit Secrets!")
            else:
                img_data = None
                try:
                    if canvas_result is not None and canvas_result.image_data is not None:
                        img_data = canvas_result.image_data
                except Exception as e:
                    st.warning(f"Could not read canvas image data: {e}")

                if img_data is not None:
                    with st.spinner("Analyzing Chinese handwriting with Gemini AI..."):
                        is_correct, feedback = grade_handwriting_with_gemini(
                            img_data, target_word, GEMINI_API_KEY
                        )
                        if is_correct:
                            st.success(f"🌟 Correct! Awesome handwriting: **{target_word}**")
                            st.write(f"💬 {feedback}")
                            st.session_state.quiz_score += 1
                            st.session_state.mastered_words.add(target_word)
                        else:
                            st.error(f"❌ Target Character: **{target_word}**")
                            st.write(f"💬 {feedback}")
                            st.session_state.unfamiliar_words.add(target_word)
                        st.session_state.quiz_checked = True
                else:
                    st.warning("✏️ Canvas stroke data empty! Write on the pad before clicking Grade.")
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
