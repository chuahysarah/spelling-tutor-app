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


@st.cache_data(ttl=3600, show_spinner=False)
def get_available_models(api_key: str) -> list[str]:
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            models_data = resp.json().get("models", [])
            valid = [m.get("name", "").replace("models/", "") for m in models_data if "generateContent" in m.get("supportedGenerationMethods", []) and "flash" in m.get("name", "").lower()]
            if valid:
                return valid
    except Exception:
        pass
    return ["gemini-2.5-flash", "gemini-1.5-flash-latest"]


def get_analysis(words: list[str], api_key: str | None) -> tuple[dict[str, dict[str, Any]], str | None]:
    if not api_key:
        return {}, "No API key configured."
    
    prompt = """You are a careful primary-school spelling tutor. Analyze every item below. Return ONLY a JSON object keyed by the exact input item. For each item, provide: language ('English' or 'Chinese'); syllables (English syllables separated with hyphens; for Chinese give one syllable per character, preferably tone-marked pinyin); meaning (simple child-friendly definition/translation); sentence (short context sentence); spelling_tip (one memorable spelling/phonics tip, mention silent letters/prefix/suffix if applicable); pinyin (Chinese tone-marked pinyin or empty for English); stroke_count (integer only if you are confident, otherwise null); radical (Chinese radical or empty); structure (e.g. 左右结构/上下结构/独体字 or empty); strokes (a concise ordered list of stroke names for each character as strings, e.g. ['横','竖','撇','捺']; do not invent detailed paths). Items: """ + json.dumps(words, ensure_ascii=False)
    
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2}}
    models_to_try = get_available_models(api_key)
    last_err = None

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            resp = requests.post(url, json=payload, timeout=8)
            if resp.status_code == 200:
                data = json.loads(resp.json()["candidates"][0]["content"]["parts"][0]["text"])
                return (data if isinstance(data, dict) else {}), None
            else:
                last_err = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
        except Exception as exc:
            last_err = str(exc)

    return {}, last_err or "Failed to connect to Gemini API."


@st.cache_data(show_spinner=False, max_entries=256)
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


st.title("📖 Step 2: Let's Learn Our Words!")

raw_words = st.session_state.get("raw_words", "")
if not raw_words:
    st.info("👆 Please go to the Home page to add your spelling list first!")
    st.stop()

words = [line.strip() for line in raw_words.replace("，", "\n").replace(",", "\n").splitlines() if line.strip()]
key = st.session_state.get("api_key")
analysis = {}

if key:
    with st.spinner("✨ Fetching study notes..."):
        analysis, _ = get_analysis(words, key)

for index, word in enumerate(words):
    info = analysis.get(word, {})
    lang = str(info.get("language") or guess_language(word))
    with st.expander(f"Word {index + 1}:  {word} ({lang})"):
        audio_button(word, lang, f"audio-{word}")
        if lang == "English":
            st.write(f"🧩 **Syllables:** {info.get('syllables', '—')}")
            st.write(f"💡 **Meaning:** {info.get('meaning', '—')}")
            st.write(f"💬 **Example:** {info.get('sentence', '—')}")
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
