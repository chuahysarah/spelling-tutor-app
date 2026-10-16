from __future__ import annotations

import datetime
import io
import json
import re
import requests
import streamlit as st
import streamlit.components.v1 as components
from gtts import gTTS
from streamlit_drawable_canvas import st_canvas

st.set_page_config(
    page_title="Dictation Quiz 🎯",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="expanded"
)

API_URL = st.secrets.get("GSHEETS_API_URL", "").strip()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600;700&display=swap');

html, body, [class*="css"], button, input, select {
    font-family: 'Fredoka', cursive, sans-serif !important;
    font-size: 1.25rem;
}

h1 { font-size: 2.8rem !important; color: #0284c7 !important; }
h2 { font-size: 2.2rem !important; color: #0369a1 !important; }
h3 { font-size: 1.8rem !important; color: #0f766e !important; }

.stButton > button {
    font-size: 1.35rem !important;
    font-weight: 700 !important;
    border-radius: 20px !important;
    padding: 0.7rem 1.4rem !important;
}

.stTextInput > div > div > input {
    font-size: 1.6rem !important;
    font-weight: 600 !important;
    border-radius: 16px !important;
    padding: 0.6rem 1rem !important;
    border: 3px solid #bae6fd !important;
}

[data-testid="stSidebar"] {
    background-color: #e0f2fe !important;
    border-right: 4px solid #bae6fd !important;
}

[data-testid="stSidebarCollapseButton"] button {
    background-color: #fde047 !important;
    border: 2px solid #eab308 !important;
    border-radius: 12px !important;
}

[data-testid="stSidebar"] .stSelectbox {
    background: #ffffff;
    padding: 10px;
    border-radius: 16px;
    border: 2px solid #bae6fd;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=15, show_spinner=False)
def fetch_available_lists(child_name: str = "") -> dict[str, str]:
    if API_URL:
        try:
            params = {"action": "get_lists"}
            if child_name:
                params["child_name"] = child_name
            resp = requests.get(API_URL, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and data:
                    return data
        except Exception:
            pass
    return {}


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


def sync_child_profiles(children: list[str]) -> None:
    if API_URL:
        try:
            requests.post(API_URL, json={"action": "save_profiles", "children": children}, timeout=5)
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Failed to sync profiles: {e}")


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
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Failed to log quiz attempt: {e}")


@st.cache_data(show_spinner=False, max_entries=256, ttl=3600)
def generate_speech_audio(text: str, lang: str) -> bytes:
    fp = io.BytesIO()
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.write_to_fp(fp)
    return fp.getvalue()


def speak_text(text: str):
    try:
        lang = 'zh-cn' if re.search(r'[\u4e00-\u9fff]', text) else 'en'
        audio_bytes = generate_speech_audio(text, lang)
        st.audio(audio_bytes, format="audio/mp3", autoplay=True)
    except Exception:
        st.warning("Audio playback failed.")


def render_hanzi_animations(word: str) -> None:
    chinese_chars = [char for char in word if re.search(r"[\u3400-\u9fff]", char)]
    if not chinese_chars:
        return

    targets = ""
    scripts = ""
    for i, char in enumerate(chinese_chars):
        div_id = f"target-{i}-{ord(char)}"
        targets += f'<div id="{div_id}" style="display:inline-block; margin: 4px; border: 3px solid #bae6fd; border-radius: 16px; background: #ffffff;"></div>'
        scripts += f"HanziWriter.create('{div_id}', '{char}', {{width: 110, height: 110, padding: 6, showOutline: true, strokeAnimationSpeed: 1.5, delayBetweenStrokes: 80}}).loopCharacterAnimation();\n"

    num_rows = (len(chinese_chars) + 2) // 3
    html_code = f"""<!DOCTYPE html><html><head><script src="https://cdn.jsdelivr.net/npm/hanzi-writer@3.5/dist/hanzi-writer.min.js"></script></head><body style="margin:0;padding:0;background:transparent;"><div style="display:flex;flex-wrap:wrap;gap:10px;justify-content:center;align-items:center;">{targets}</div><script>{scripts}</script></body></html>"""
    components.html(html_code, height=num_rows * 125 + 15)


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
    st.session_state[f"quiz_result_{child_name}"] = None
    st.session_state[f"mastered_words_{child_name}"] = set()
    st.session_state[f"unfamiliar_words_{child_name}"] = set()


def rename_child_profile(old_name: str, new_name: str):
    if not new_name or new_name == old_name:
        return
    if old_name in st.session_state.children:
        idx = st.session_state.children.index(old_name)
        st.session_state.children[idx] = new_name
    
    st.session_state.active_child = new_name

    for key_prefix in ["active_week", "raw_words", "cached_analysis", "quiz_index", "quiz_score", "quiz_checked", "quiz_logged", "quiz_result", "mastered_words", "unfamiliar_words"]:
        old_key = f"{key_prefix}_{old_name}"
        new_key = f"{key_prefix}_{new_name}"
        if old_key in st.session_state:
            st.session_state[new_key] = st.session_state.pop(old_key)

    sync_child_profiles(st.session_state.children)


if "children" not in st.session_state:
    st.session_state.children = fetch_child_profiles()
if "active_child" not in st.session_state:
    st.session_state.active_child = st.session_state.children[0]

with st.sidebar:
    st.subheader("👤 Practicing Learner")
    selected_child = st.selectbox(
        "Current Child:",
        options=st.session_state.children,
        index=st.session_state.children.index(st.session_state.active_child) if st.session_state.active_child in st.session_state.children else 0
    )
    if selected_child != st.session_state.active_child:
        st.session_state.active_child = selected_child
        st.rerun()

    active_child = st.session_state.active_child

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

available_lists = fetch_available_lists(active_child)
list_titles = list(available_lists.keys())

if not list_titles:
    st.info(f"📋 No dictation lists assigned to {active_child} yet. Grown-ups can add lists on the home page!")
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
if f"quiz_result_{active_child}" not in st.session_state:
    st.session_state[f"quiz_result_{active_child}"] = None
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

st.write("### 🔊 Listen to the Word:")
audio_col1, audio_col2 = st.columns([1, 2])
with audio_col1:
    if st.button("🔊 Play Sound", type="primary", use_container_width=True):
        speak_text(target_word)

st.write("---")

if is_chinese:
    if st.session_state[f"quiz_checked_{active_child}"]:
        col_pad, col_ref = st.columns([1, 1], gap="medium")
    else:
        col_pad, col_ref = st.columns([1, 0.01])

    with col_pad:
        st.markdown("### ✏️ Your Chinese Writing Pad")
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=7,
            stroke_color="#000000",
            background_color="#ffffff",
            height=280,
            width=280,
            drawing_mode="freedraw",
            update_streamlit=False,
            return_image_data=True,
            key=f"canvas_{active_child}_{selected_list_title}_{current_idx}"
        )

    with col_ref:
        if st.session_state[f"quiz_checked_{active_child}"]:
            st.markdown(f"### 🔍 Correct Word: **{target_word}**")
            render_hanzi_animations(target_word)

    st.write("---")

    if not st.session_state[f"quiz_checked_{active_child}"]:
        btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
        with btn_col2:
            if st.button("🔍 Check Answer & Stroke Order", type="primary", use_container_width=True):
                st.session_state[f"quiz_checked_{active_child}"] = True
                st.rerun()
    else:
        if st.session_state[f"quiz_result_{active_child}"] is None:
            st.markdown("<h3 style='text-align: center;'>📝 How did your writing look?</h3>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            
            with c1:
                if st.button("🌟 Pass / Correct", type="primary", use_container_width=True):
                    st.session_state[f"quiz_score_{active_child}"] += 1
                    st.session_state[f"mastered_words_{active_child}"].add(target_word)
                    st.session_state[f"quiz_result_{active_child}"] = "correct"
                    st.rerun()

            with c2:
                if st.button("❌ Needs Practice", type="secondary", use_container_width=True):
                    st.session_state[f"unfamiliar_words_{active_child}"].add(target_word)
                    st.session_state[f"quiz_result_{active_child}"] = "incorrect"
                    st.rerun()

        else:
            if st.session_state[f"quiz_result_{active_child}"] == "correct":
                st.success(f"🌟 Marked Correct! Great job, {active_child}!")
            else:
                st.warning(f"💡 Marked for practice! Keep it up, {active_child}!")

            btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
            with btn_col2:
                if st.button("➡️ Next Word", type="primary", use_container_width=True):
                    st.session_state[f"quiz_index_{active_child}"] += 1
                    st.session_state[f"quiz_checked_{active_child}"] = False
                    st.session_state[f"quiz_result_{active_child}"] = None
                    st.rerun()

else:
    st.markdown("### 🔤 Type Your English Spelling Answer:")
    
    typed_ans = st.text_input(
        "Type word here:",
        placeholder="Type the word you heard...",
        key=f"eng_input_{active_child}_{selected_list_title}_{current_idx}",
        disabled=st.session_state[f"quiz_checked_{active_child}"]
    )

    st.write("")

    if not st.session_state[f"quiz_checked_{active_child}"]:
        btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
        with btn_col2:
            if st.button("✅ Check English Spelling", type="primary", use_container_width=True):
                clean_user = typed_ans.strip().casefold()
                clean_target = target_word.strip().casefold()
                
                if clean_user == clean_target:
                    st.session_state[f"quiz_score_{active_child}"] += 1
                    st.session_state[f"mastered_words_{active_child}"].add(target_word)
                    st.session_state[f"quiz_result_{active_child}"] = "correct"
                else:
                    st.session_state[f"unfamiliar_words_{active_child}"].add(target_word)
                    st.session_state[f"quiz_result_{active_child}"] = "incorrect"

                st.session_state[f"quiz_checked_{active_child}"] = True
                st.rerun()

    else:
        if st.session_state[f"quiz_result_{active_child}"] == "correct":
            st.success(f"🌟 Correct Spelling! Awesome job, {active_child}: **{target_word}**")
        else:
            st.error(f"❌ Correct Spelling: **{target_word}**")

        st.write("")
        btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
        with btn_col2:
            if st.button("➡️ Next Word", type="primary", use_container_width=True):
                st.session_state[f"quiz_index_{active_child}"] += 1
                st.session_state[f"quiz_checked_{active_child}"] = False
                st.session_state[f"quiz_result_{active_child}"] = None
                st.rerun()
