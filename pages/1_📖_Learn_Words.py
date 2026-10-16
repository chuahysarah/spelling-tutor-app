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
   - For CHINESE: Use a playful mix of English and Chinese! (e.g., "Look at the left side! It has '口' (mouth) because...", "Fun story: '休' is a person '人' leaning against a tree '木' to rest!").
   - For ENGLISH: Use fun mnemonics or phonics rules (e.g., "Big Elephants Are Ugly = B-E-A-U-tiful!").
6. pinyin: Chinese tone-marked pinyin or empty for English.

Items: """ + json.dumps(words, ensure_ascii=False)
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}], 
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.3}
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }

    urls_to_try = [
        "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    ]

    last_err = None
    for url in urls_to_try:
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=12)
            if resp.status_code == 200:
                data = json.loads(resp.json()["candidates"][0]["content"]["parts"][0]["text"])
                return (data if isinstance(data, dict) else {}), None
            else:
                last_err = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
        except Exception as exc:
            last_err = str(exc)

    return {}, last_err or "Failed to connect to Gemini API."


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

if "archived_lists" in st.session_state and st.session_state.archived_lists:
    options_list = list(st.session_state.archived_lists.keys())
    curr_index = options_list.index(st.session_state.get("active_week", options_list[0])) if st.session_state.get("active_week") in options_list else 0
    selected_week = st.selectbox(
        "📚 Active Practice List:",
        options=options_list,
        index=curr_index
    )
    if selected_week != st.session_state.get("active_week"):
        st.session_state.active_week = selected_week
        st.session_state.raw_words = st.session_state.archived_lists[selected_week]
        st.session_state.cached_analysis = {}
        st.rerun()

raw_words = st.session_state.get("raw_words", "")
if not raw_words:
    st.info("👆 Please go to the Home page to add or select your spelling list first!")
    st.stop()

words = [line.strip() for line in raw_words.replace("，", "\n").replace(",", "\n").splitlines() if line.strip()]

if "cached_analysis" not in st.session_state:
    st.session_state.cached_analysis = {}

key = get_api_key()

if key and not st.session_state.cached_analysis and words:
    with st.spinner("✨ Fetching child-friendly meanings and memory tricks..."):
        data, err = get_analysis(words, key)
        if not err and data:
            st.session_state.cached_analysis = data
        elif err:
            st.warning(f"Note: Unable to load AI details ({err}).")

analysis = st.session_state.cached_analysis

if not key:
    st.warning("⚠️ No Gemini API Key configured in Secrets.")

for index, word in enumerate(words):
    info = analysis.get(word, {})
    lang = str(info.get("language") or guess_language(word))
    with st.expander(f"Word {index + 1}:  {word} ({lang})", expanded=True):
        audio_button(word, lang, f"audio-{word}")
        if lang == "English":
            st.write(f"🧩 **Syllables:** {info.get('syllables', '—')}")
            st.write(f"💡 **Meaning:** {info.get('meaning', '—')}")
            st.write(f"💬 **Example:** {info.get('sentence', '—')}")
            st.write(f"⭐ **Fun Memory Tip:** {info.get('spelling_tip', '—')}")
        else:
            py = str(info.get("pinyin") or local_pinyin(word))
            st.write(f"🗣️ **Pinyin:** `{py}`")
            st.write("✍️ **Stroke Order Animation:**")
            render_hanzi_animations(word)
            st.write(f"💡 **Meaning:** {info.get('meaning', '—')}")
            sentence = info.get("sentence", "—")
            st.write(f"💬 **Example:** {sentence}")
            if sentence and sentence != "—":
                audio_button(sentence, "Chinese", f"sentence-{word}")
            st.write(f"⭐ **Fun Memory Tip (记忆小贴士):** {info.get('spelling_tip', '—')}")
