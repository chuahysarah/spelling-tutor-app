from __future__ import annotations

import json
import os
import re
from typing import Any

import requests
import streamlit as st
import streamlit.components.v1 as components
from gtts import gTTS
from pypinyin import Style, pinyin

st.set_page_config(page_title="Learn Words 📖", page_icon="📖", layout="centered")

API_URL = st.secrets.get("GSHEETS_API_URL", "").strip()

DEFAULT_LISTS = {
    "Week 1: School & Friends": "学校\n认真\n爸爸\n妈妈\napple\nschool\nfriend",
    "Week 2: Nature & Family": "mountain\nflower\n事情\n学习"
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600;700&display=swap');

html, body, [class*="css"], button, input, select {
    font-family: 'Fredoka', cursive, sans-serif !important;
    font-size: 1.2rem;
}

h1 { font-size: 2.8rem !important; color: #0284c7 !important; }
h2 { font-size: 2.2rem !important; color: #0369a1 !important; }
h3 { font-size: 1.7rem !important; color: #0f766e !important; }

.stButton > button {
    font-size: 1.3rem !important;
    font-weight: 700 !important;
    border-radius: 18px !important;
}

.word-card {
    background: #f0f9ff;
    border-radius: 20px;
    padding: 1.2rem;
    border: 2px solid #bae6fd;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)


def fetch_available_lists() -> dict[str, str]:
    if "archived_lists" in st.session_state and st.session_state.archived_lists:
        return st.session_state.archived_lists

    if API_URL:
        try:
            resp = requests.get(API_URL, params={"action": "get_lists"}, allow_redirects=True, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and data:
                    st.session_state.archived_lists = data
                    return data
        except Exception:
            pass
    return DEFAULT_LISTS


def guess_language(text: str) -> str:
    return "Chinese" if re.search(r"[\u3400-\u9fff]", text) else "English"


def local_pinyin(text: str) -> str:
    return " ".join(part[0] for part in pinyin(text, style=Style.TONE, heteronym=False, errors=lambda x: list(x)))


def get_api_key() -> str:
    key = ""
    if "GEMINI_API_KEY" in st.secrets:
        key = str(st.secrets["GEMINI_API_KEY"])
    elif "gemini_api_key" in st.secrets:
        key = str(st.secrets["gemini_api_key"])
    elif st.session_state.get("api_key"):
        key = str(st.session_state.get("api_key"))
    
    return key.strip().strip("'").strip('"')


def get_analysis(words: list[str], api_key: str) -> tuple[dict[str, dict[str, Any]], str | None]:
    if not api_key:
        return {}, "No API key configured."
    
    prompt = """You are an encouraging primary school spelling tutor for a 7-9 year old child. Analyze every item below. Return ONLY a JSON object keyed by the exact input item.

For each item, provide:
1. language: 'English' or 'Chinese'
2. syllables: English syllables with hyphens; for Chinese give tone-marked pinyin.
3. meaning: simple, fun, child-friendly definition (mix English/Chinese explanations so primary school kids understand easily).
4. sentence: short, relatable daily life context sentence.
5. spelling_tip: a super fun, child-friendly memory trick or phonics hint! 
   - For CHINESE: Use a playful mix of English and Chinese! (e.g., "Look at the left side! It has '口' (mouth)...", "Fun story: '休' is a person '人' leaning against a tree '木' to rest!").
   - For ENGLISH: Use fun mnemonics or phonics rules (e.g., "Big Elephants Are Ugly = B-E-A-U-tiful!").
6. pinyin: Chinese tone-marked pinyin or empty for English.

Items: """ + json.dumps(words, ensure_ascii=False)
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}], 
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.3}
    }
    
    clean_token = api_key.strip().strip("'").strip('"')
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={clean_token}"

    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        if resp.status_code == 200:
            raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return (data if isinstance(data, dict) else {}), None
    except Exception as exc:
        return {}, str(exc)

    return {}, "Failed to load AI details."


@st.cache_data(show_spinner=False, max_entries=512, ttl=7200)
def make_audio(text: str, lang: str) -> bytes:
    from io import BytesIO
    audio = BytesIO()
    gTTS(text=text, lang=lang, slow=False).write_to_fp(audio)
    return audio.getvalue()


def audio_button(text: str, language: str, key: str) -> None:
    lang = "zh-CN" if language == "Chinese" else "en"
    try:
        st.audio(make_audio(text, lang), format="audio/mp3")
    except Exception:
        st.caption("🔊 Audio temporarily unavailable")


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

    num_rows = (len(chinese_chars) + 3) // 4
    html_code = f"""<!DOCTYPE html><html><head><script src="https://cdn.jsdelivr.net/npm/hanzi-writer@3.5/dist/hanzi-writer.min.js"></script></head><body style="margin:0;padding:0;background:transparent;"><div style="display:flex;flex-wrap:wrap;gap:10px;justify-content:center;">{targets}</div><script>{scripts}</script></body></html>"""
    components.html(html_code, height=num_rows * 125 + 20)


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

    with st.expander("✏️ Edit Learner Name", expanded=False):
        edited_name = st.text_input("New Name:", value=active_child, key=f"p1_rename_input_{active_child}")
        if st.button("Save New Name", type="primary", use_container_width=True):
            clean_rename = edited_name.strip()
            if clean_rename and clean_rename != active_child:
                rename_child_profile(active_child, clean_rename)
                st.success(f"Renamed to {clean_rename}!")
                st.rerun()

active_child = st.session_state.active_child

st.title(f"📖 Hi {active_child}! Let's Learn Our Words!")

available_lists = fetch_available_lists()
list_titles = list(available_lists.keys())

current_active = st.session_state.get(f"active_week_{active_child}", "")
if current_active not in list_titles and list_titles:
    st.session_state[f"active_week_{active_child}"] = list_titles[0]
    st.session_state[f"raw_words_{active_child}"] = available_lists[list_titles[0]]

default_idx = list_titles.index(st.session_state[f"active_week_{active_child}"]) if st.session_state[f"active_week_{active_child}"] in list_titles else 0

selected_week = st.selectbox(
    f"📚 Select Weekly List for {active_child}:",
    options=list_titles,
    index=default_idx
)

if selected_week != st.session_state.get(f"active_week_{active_child}"):
    st.session_state[f"active_week_{active_child}"] = selected_week
    st.session_state[f"raw_words_{active_child}"] = available_lists[selected_week]
    st.session_state[f"cached_analysis_{active_child}"] = {}
    st.rerun()

raw_words = st.session_state.get(f"raw_words_{active_child}", "")
words = [line.strip() for line in raw_words.replace("，", "\n").replace(",", "\n").splitlines() if line.strip()]

if not words:
    st.warning("⚠️ No words found in the selected list. Please choose a different list above!")
    st.stop()

if f"cached_analysis_{active_child}" not in st.session_state:
    st.session_state[f"cached_analysis_{active_child}"] = {}

key = get_api_key()

if key and not st.session_state.get(f"cached_analysis_{active_child}") and words:
    with st.spinner(f"✨ Loading word details for {active_child}..."):
        data, err = get_analysis(words, key)
        if not err and data:
            st.session_state[f"cached_analysis_{active_child}"] = data

analysis = st.session_state.get(f"cached_analysis_{active_child}", {})

for index, word in enumerate(words):
    info = analysis.get(word, {})
    lang = str(info.get("language") or guess_language(word))
    with st.expander(f"Word {index + 1}:  {word} ({lang})", expanded=True):
        audio_button(word, lang, f"audio-{word}")
        if lang == "English":
            syllables = info.get('syllables') or "-".join([word[i:i+3] for i in range(0, len(word), 3)])
            meaning = info.get('meaning') or f"The English word '{word}'."
            sentence = info.get('sentence') or f"Please write the word '{word}' in your notebook."
            tip = info.get('spelling_tip') or f"Break '{word}' down into smaller letter chunks to remember!"
            
            st.write(f"🧩 **Syllables:** {syllables}")
            st.write(f"💡 **Meaning:** {meaning}")
            st.write(f"💬 **Example:** {sentence}")
            st.write(f"⭐ **Fun Memory Tip:** {tip}")
        else:
            py = str(info.get("pinyin") or local_pinyin(word))
            meaning = info.get('meaning') or f"Chinese word / 词语: {word}"
            sentence = info.get("sentence") or f"今天我们要学习 '{word}' 这个词。"
            tip = info.get('spelling_tip') or f"Observe the stroke order and practice writing '{word}' step-by-step!"

            st.write(f"🗣️ **Pinyin:** `{py}`")
            st.write("✍️ **Stroke Order Animation:**")
            render_hanzi_animations(word)
            st.write(f"💡 **Meaning:** {meaning}")
            st.write(f"💬 **Example:** {sentence}")
            if sentence:
                audio_button(sentence, "Chinese", f"sentence-{word}")
            st.write(f"⭐ **Fun Memory Tip (记忆小贴士):** {tip}")
