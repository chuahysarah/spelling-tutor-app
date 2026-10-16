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


def fetch_available_lists() -> dict[str, str]:
    """Fetches word lists from session state or Google Sheets API on direct cold start."""
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
    
    clean_key = api_key.strip().strip("'").strip('"')
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": clean_key
    }

    url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=12)
        if resp.status_code == 200:
            raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return (data if isinstance(data, dict) else {}), None
        else:
            fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={clean_key}"
            resp_fb = requests.post(fallback_url, json=payload, headers={"Content-Type": "application/json"}, timeout=12)
            if resp_fb.status_code == 200:
                raw_text = resp_fb.json()["candidates"][0]["content"]["parts"][0]["text"]
                match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                    return (data if isinstance(data, dict) else {}), None
            return {}, resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
    except Exception as exc:
        return {}, str(exc)


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
        targets += f'<div id="{div_id}" style="display:inline-block; margin: 4px; border: 2px solid #bae6fd; border-radius: 12px; background: #ffffff;"></div>'
        scripts += f"HanziWriter.create('{div_id}', '{char}', {{width: 90, height: 90, padding: 4, showOutline: true, strokeAnimationSpeed: 1.5, delayBetweenStrokes: 80}}).loopCharacterAnimation();\n"

    num_rows = (len(chinese_chars) + 4) // 5
    html_code = f"""<!DOCTYPE html><html><head><script src="https://cdn.jsdelivr.net/npm/hanzi-writer@3.5/dist/hanzi-writer.min.js"></script></head><body style="margin:0;padding:0;background:transparent;"><div style="display:flex;flex-wrap:wrap;gap:6px;">{targets}</div><script>{scripts}</script></body></html>"""
    components.html(html_code, height=num_rows * 110 + 15)


with st.sidebar:
    st.subheader("👨‍👩‍👧 For Grown-Ups")
    api_key_input = st.text_input("Google Gemini API Key (optional)", type="password", value="")
    if api_key_input:
        st.session_state.api_key = api_key_input.strip()

st.title("📖 Step 2: Let's Learn Our Words!")

# Ensure archived_lists and active_week are populated on cold start
available_lists = fetch_available_lists()
list_titles = list(available_lists.keys())

current_active = st.session_state.get("active_week", "")
if current_active not in list_titles and list_titles:
    st.session_state.active_week = list_titles[0]
    st.session_state.raw_words = available_lists[list_titles[0]]

default_idx = list_titles.index(st.session_state.active_week) if st.session_state.active_week in list_titles else 0

selected_week = st.selectbox(
    "📚 Active Practice List:",
    options=list_titles,
    index=default_idx
)

if selected_week != st.session_state.get("active_week"):
    st.session_state.active_week = selected_week
    st.session_state.raw_words = available_lists[selected_week]
    st.session_state.cached_analysis = {}
    st.rerun()

raw_words = st.session_state.get("raw_words", "")
words = [line.strip() for line in raw_words.replace("，", "\n").replace(",", "\n").splitlines() if line.strip()]

if not words:
    st.warning("⚠️ No words found in the selected list. Please select a different list above!")
    st.stop()

if "cached_analysis" not in st.session_state:
    st.session_state.cached_analysis = {}

key = get_api_key()

if key and not st.session_state.cached_analysis and words:
    with st.spinner("✨ Fetching child-friendly meanings and memory tricks..."):
        data, err = get_analysis(words, key)
        if not err and data:
            st.session_state.cached_analysis = data
        elif err:
            st.warning(f"Note: Unable to load AI details ({err}). Using standard word details.")

analysis = st.session_state.cached_analysis

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
