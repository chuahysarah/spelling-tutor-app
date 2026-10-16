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


def log_completed_quiz(child_name: str, week_title: str, score: int, total_words: int, mastered: set, unfamiliar: set):
    if API_URL:
        try:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            payload = {
                "action": "log_quiz",
                "timestamp": now_str,
                "child_name": child_name,
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
    try:
        clean_token = api_key.strip().strip("'").strip('"')
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

        headers_bearer = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {clean_token}"
        }

        headers_goog = {
            "Content-Type": "application/json",
            "x-goog-api-key": clean_token
        }

        resp = requests.post(url, json=payload, headers=headers_bearer, timeout=12)

        if resp.status_code == 200:
            res_json = resp.json()
            text_resp = res_json['candidates'][0]['content']['parts'][0]['text']
            match = re.search(r'\{.*\}', text_resp, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                return parsed.get("is_correct", False), parsed.get("feedback", "Evaluated successfully!")
            return True, "Handwriting evaluated!"

        resp_fb = requests.post(url, json=payload, headers=headers_goog, timeout=12)
        if resp_fb.status_code == 200:
            res_json = resp_fb.json()
            text_resp = res_json['candidates'][0]['content']['parts'][0]['text']
            match = re.search(r'\{.*\}', text_resp, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                return parsed.get("is_correct", False), parsed.get("feedback", "Evaluated successfully!")
            return True, "Handwriting evaluated!"
            
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


def reset_quiz_state(child_name: str):
    st.session_state[f"quiz_index_{child_name}"] = 0
    st.session_state[f"quiz_score_{child_name}"] = 0
    st.session_state[f"quiz_checked_{child_name}"] = False
    st.session_state[f"quiz_logged_{child_name}"] = False
    st.session_state[f"mastered_words_{child_name}"] = set()
    st.session_state[f"unfamiliar_words_{child_name}"] = set()


def rename_child_profile(old_name: str, new_name: str):
    if not new_name or new_name == old_name:
        return
    if old_name in st.session_state.children:
        idx = st.session_state.children.index(old_name)
        st.session_state.children[idx] = new_name
    
    st.session_state.active_child = new_name

    for key_prefix in ["active_week", "raw_words", "cached_analysis", "quiz_index", "quiz_score", "quiz_checked", "quiz_logged", "mastered_words", "unfamiliar_words"]:
        old_key = f"{key_prefix}_{old_name}"
        new_key = f"{key_prefix}_{new_name}"
        if old_key in st.session_state:
            st.session_state[new_key] = st.session_state.pop(old_key)


# Sidebar Child Switcher
if "children" not in st.session_state:
    st.session_state.children = ["Alex", "Emma"]
if "active_child" not in st.session_state:
    st.session_state.active_child = st.session_state.children[0]

with st.sidebar:
    st.subheader("👤 Practicing Learner")
    selected_child = st.selectbox(
        "Current Child:",
        options=st.session_state.children,
        index=st.session_state.children.index(st.session_state.active_child)
    )
    if selected_child != st.session_state.active_child:
        st.session_state.active_child = selected_child
        st.rerun()

    active_child = st.session_state.active_child

    # Edit Name
    with st.expander("✏️ Edit Learner Name", expanded=False):
        edited_name = st.text_input("New Name:", value=active_child, key=f"p2_rename_input_{active_child}")
        if st.button("Save New Name", type="primary", use_container_width=True):
            clean_rename = edited_name.strip()
            if clean_rename and clean_rename != active_child:
                rename_child_profile(active_child, clean_rename)
                st.success(f"Renamed to {clean_rename}!")
                st.rerun()

active_child = st.session_state.active_child

st.title(f"🎯 Hi {active_child}! Dictation Quiz Time!")

available_lists = fetch_available_lists()
list_titles = list(available_lists.keys())

if not list_titles:
    st.warning("⚠️ No spelling lists available. Please create a list on the home page first!")
    st.stop()

current_active = st.session_state.get(f"active_week_{active_child}", "")
if current_active not in list_titles and list_titles:
    st.session_state[f"active_week_{active_child}"] = list_titles[0]
    st.session_state[f"raw_words_{active_child}"] = available_lists[list_titles[0]]
    reset_quiz_state(active_child)

default_idx = list_titles.index(st.session_state[f"active_week_{active_child}"]) if st.session_state[f"active_week_{active_child}"] in list_titles else 0

selected_list_title = st.selectbox(
    f"📋 Select Dictation List for {active_child}:",
    options=list_titles,
    index=default_idx
)

if selected_list_title != st.session_state.get(f"active_week_{active_child}"):
    st.session_state[f"active_week_{active_child}"] = selected_list_title
    st.session_state[f"raw_words_{active_child}"] = available_lists[selected_list_title]
    reset_quiz_state(active_child)
    st.rerun()

quiz_words = normalize_words(st.session_state.get(f"raw_words_{active_child}", ""))

if not quiz_words:
    st.warning("⚠️ No words found in the selected list. Please choose a different list above!")
    st.stop()

if f"quiz_index_{active_child}" not in st.session_state:
    st.session_state[f"quiz_index_{active_child}"] = 0
if f"quiz_score_{active_child}" not in st.session_state:
    st.session_state[f"quiz_score_{active_child}"] = 0
if f"quiz_checked_{active_child}" not in st.session_state:
    st.session_state[f"quiz_checked_{active_child}"] = False
if f"quiz_logged_{active_child}" not in st.session_state:
    st.session_state[f"quiz_logged_{active_child}"] = False
if f"mastered_words_{active_child}" not in st.session_state:
    st.session_state[f"mastered_words_{active_child}"] = set()
if f"unfamiliar_words_{active_child}" not in st.session_state:
    st.session_state[f"unfamiliar_words_{active_child}"] = set()

total_q = len(quiz_words)
current_idx = st.session_state[f"quiz_index_{active_child}"]

if current_idx >= total_q:
    st.balloons()
    st.success(f"🎉 Quiz Completed! Outstanding effort, {active_child}!")
    
    final_score = st.session_state[f"quiz_score_{active_child}"]
    st.metric(label="Final Score", value=f"{final_score} / {total_q}")

    if not st.session_state[f"quiz_logged_{active_child}"]:
        log_completed_quiz(
            child_name=active_child,
            week_title=selected_list_title,
            score=final_score,
            total_words=total_q,
            mastered=st.session_state[f"mastered_words_{active_child}"],
            unfamiliar=st.session_state[f"unfamiliar_words_{active_child}"]
        )
        st.session_state[f"quiz_logged_{active_child}"] = True
        st.info(f"✅ {active_child}'s score and practice details have been saved to Parent History!")

    if st.button("🔄 Restart Quiz", type="primary"):
        reset_quiz_state(active_child)
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
    key=f"canvas_{active_child}_{selected_list_title}_{current_idx}"
)

if not is_chinese:
    user_answer = st.text_input("Type your spelling answer here:", key=f"quiz_ans_{active_child}_{selected_list_title}_{current_idx}")

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
                            st.success(f"🌟 Correct! Awesome handwriting, {active_child}: **{target_word}**")
                            st.write(f"💬 {feedback}")
                            st.session_state[f"quiz_score_{active_child}"] += 1
                            st.session_state[f"mastered_words_{active_child}"].add(target_word)
                        else:
                            st.error(f"❌ Target Character: **{target_word}**")
                            st.write(f"💬 {feedback}")
                            st.session_state[f"unfamiliar_words_{active_child}"].add(target_word)
                        st.session_state[f"quiz_checked_{active_child}"] = True
                else:
                    st.warning("✏️ Canvas stroke data empty! Write on the pad before clicking Grade.")
        else:
            clean_user = user_answer.strip().casefold() if 'user_answer' in locals() else ""
            clean_target = target_word.strip().casefold()
            if clean_user == clean_target:
                st.success(f"🌟 Correct! Awesome job, {active_child}: **{target_word}**")
                st.session_state[f"quiz_score_{active_child}"] += 1
                st.session_state[f"mastered_words_{active_child}"].add(target_word)
            else:
                st.error(f"❌ Correct Spelling: **{target_word}**")
                st.session_state[f"unfamiliar_words_{active_child}"].add(target_word)

            st.session_state[f"quiz_checked_{active_child}"] = True

with col2:
    if st.session_state[f"quiz_checked_{active_child}"]:
        if st.button("➡️ Next Word", type="secondary"):
            st.session_state[f"quiz_index_{active_child}"] += 1
            st.session_state[f"quiz_checked_{active_child}"] = False
            st.rerun()
