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
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="Magic Spelling World ✏️", page_icon="⭐", layout="centered")

# Child-friendly custom styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Fredoka', cursive, sans-serif;
}

.block-container {
    max-width: 900px; 
    padding-top: 1.5rem; 
    padding-bottom: 3rem;
}

.hero {
    padding: 1.5rem 1.8rem; 
    border-radius: 24px; 
    background: linear-gradient(135deg, #fef9c3 0%, #e0f2fe 100%); 
    border: 3px solid #fde047;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
    margin-bottom: 1.25rem;
    text-align: center;
}

.hero h1 {
    margin: 0 0 .35rem 0; 
    color: #0284c7;
    font-size: 2.2rem;
    font-weight: 700;
}

.hero-subtitle {
    color: #475569;
    font-size: 1.1rem;
}

.word-card {
    padding: 1.2rem 1.5rem; 
    border: 2px solid #bae6fd; 
    border-radius: 20px; 
    background: #ffffff; 
    margin: .6rem 0;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);
}

.stButton>button {
    border-radius: 16px !important;
    font-weight: 600 !important;
    font-size: 1.05rem !important;
    padding: 0.5rem 1.2rem !important;
    transition: transform 0.1s ease;
}

.stButton>button:active {
    transform: scale(0.97);
}

div[data-testid="stExpander"] {
    border-radius: 18px !important;
    border: 2px solid #e2e8f0 !important;
    background-color: #ffffff;
    margin-bottom: 0.75rem;
}
</style>
<div class="hero">
    <h1>🌟 Magic Spelling Practice! ✏️</h1>
    <div class="hero-subtitle">Listen, practice writing, and become a spelling star! 听写 / 默写 小助手</div>
</div>
""", unsafe_allow_html=True)


def get_api_key() -> str | None:
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    try:
        key = key or st.secrets.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    except Exception:
        pass
    return key.strip() if key else None


def guess_language(text: str) -> str:
    return "Chinese" if re.search(r"[\u3400-\u9fff]", text) else "English"


def normalize_words(raw: str) -> list[str]:
    seen: set[str] = set()
    result = []
    for line in raw.replace("，", "\n").replace(",", "\n").splitlines():
        item = line.strip()
        if item and item.casefold() not in seen:
            seen.add(item.casefold())
            result.append(item)
    return result


def local_pinyin(text: str) -> str:
    return " ".join(part[0] for part in pinyin(text, style=Style.TONE, heteronym=False, errors=lambda x: list(x)))


@st.cache_data(ttl=3600, show_spinner=False)
def get_available_models(api_key: str) -> list[str]:
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            models_data = resp.json().get("models", [])
            valid_models = []
            for m in models_data:
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods and "flash" in name.lower():
                    valid_models.append(name)
            if valid_models:
                return valid_models
    except Exception:
        pass
    return ["gemini-2.5-flash", "gemini-1.5-flash-latest"]


def get_analysis(words: list[str], api_key: str | None) -> tuple[dict[str, dict[str, Any]], str | None]:
    if not api_key:
        return {}, "No API key configured."
    
    prompt = """You are a careful primary-school spelling tutor. Analyze every item below. Return ONLY a JSON object keyed by the exact input item. For each item, provide: language ('English' or 'Chinese'); syllables (English syllables separated with hyphens; for Chinese give one syllable per character, preferably tone-marked pinyin); meaning (simple child-friendly definition/translation); sentence (short context sentence); spelling_tip (one memorable spelling/phonics tip, mention silent letters/prefix/suffix if applicable); pinyin (Chinese tone-marked pinyin or empty for English); stroke_count (integer only if you are confident, otherwise null); radical (Chinese radical or empty); structure (e.g. 左右结构/上下结构/独体字 or empty); strokes (a concise ordered list of stroke names for each character as strings, e.g. ['横','竖','撇','捺']; do not invent detailed paths). For Chinese phrases, give pinyin and character-specific stroke count/radical/structure/stroke-order in fields as short lists where helpful. Keep explanations age-appropriate. Unknown facts should be marked null or '不确定', not guessed. Items: """ + json.dumps(words, ensure_ascii=False)
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2}
    }
    
    models_to_try = get_available_models(api_key)
    last_err = None

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            resp = requests.post(url, json=payload, timeout=10)
            res_data = resp.json()
            
            if resp.status_code == 200:
                text_content = res_data["candidates"][0]["content"]["parts"][0]["text"]
                data = json.loads(text_content)
                return (data if isinstance(data, dict) else {}), None
            else:
                last_err = res_data.get("error", {}).get("message", f"HTTP {resp.status_code}")
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
        st.caption("🔊 Audio temporary unavailable")


def render_hanzi_animations(word: str) -> None:
    chinese_chars = [char for char in word if re.search(r"[\u3400-\u9fff]", char)]
    if not chinese_chars:
        return

    targets = ""
    scripts = ""
    
    for i, char in enumerate(chinese_chars):
        div_id = f"target-{i}-{ord(char)}"
        targets += f'<div id="{div_id}" style="display:inline-block; margin: 4px; border: 2px solid #bae6fd; border-radius: 12px; background: #ffffff;"></div>'
        scripts += f"""
        HanziWriter.create('{div_id}', '{char}', {{
            width: 90,
            height: 90,
            padding: 4,
            showOutline: true,
            strokeAnimationSpeed: 1.5,
            delayBetweenStrokes: 80
        }}).loopCharacterAnimation();
        """

    chars_per_row = 5
    num_rows = (len(chinese_chars) + chars_per_row - 1) // chars_per_row
    container_height = num_rows * 110 + 15

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <script src="https://cdn.jsdelivr.net/npm/hanzi-writer@3.5/dist/hanzi-writer.min.js"></script>
    </head>
    <body style="margin: 0; padding: 0; background: transparent;">
      <div style="display: flex; flex-wrap: wrap; gap: 6px;">
        {targets}
      </div>
      <script>
        {scripts}
      </script>
    </body>
    </html>
    """
    components.html(html_code, height=container_height)


def format_strokes(strokes_val: Any) -> str:
    if not strokes_val:
        return "—"
    if isinstance(strokes_val, list):
        items = []
        for item in strokes_val:
            if isinstance(item, list):
                items.append(" ".join(str(sub) for sub in item))
            else:
                items.append(str(item))
        return "；".join(items)
    return str(strokes_val)


def show_analysis(word: str, info: dict[str, Any]) -> None:
    language = str(info.get("language") or guess_language(word))
    st.markdown(f'<div class="word-card"><h3 style="margin:0; color:#0369a1;">✨ {word}</h3></div>', unsafe_allow_html=True)
    audio_button(word, language, f"audio-{word}")
    
    if language == "English":
        cols = st.columns(2)
        cols[0].markdown(f"🧩 **Syllables:** {info.get('syllables', '—')}")
        cols[1].markdown(f"💡 **Meaning:** {info.get('meaning', '—')}")
        st.markdown(f"💬 **Example:** {info.get('sentence', '—')}")
        st.markdown(f"⭐ **Spelling Tip:** {info.get('spelling_tip', '—')}")
    else:
        py = str(info.get("pinyin") or local_pinyin(word))
        st.markdown(f"🗣️ **拼音 Pinyin:** `{py}`")
            
        st.markdown("✍️ **Stroke Order Animation (动画笔顺):**")
        render_hanzi_animations(word)

        st.markdown(f"💡 **意思 Meaning:** {info.get('meaning', '—')}")
        
        sentence = info.get("sentence", "—")
        st.markdown(f"💬 **例句 Example:** {sentence}")
        if sentence and sentence != "—":
            st.caption("🔊 Listen to the whole example sentence:")
            audio_button(sentence, "Chinese", f"sentence-audio-{word}")

        st.markdown(f"🔢 **总笔画 Stroke count:** {info.get('stroke_count') or 'Please verify with your class dictionary'}")
        st.markdown(f"🌱 **部首 Radical:** {info.get('radical') or 'Please verify with your class dictionary'}")
        st.markdown(f"🏗️ **结构 Structure:** {info.get('structure') or '—'}")
        
        strokes = info.get("strokes")
        if strokes:
            st.markdown(f"📝 **笔顺名称 Stroke names:** {format_strokes(strokes)}")
            
        st.markdown(f"⭐ **记忆小贴士 Tip:** {info.get('spelling_tip', '—')}")


# Session State Initialization
if "raw_words" not in st.session_state:
    st.session_state.raw_words = ""
if "quiz_words" not in st.session_state:
    st.session_state.quiz_words = []
if "quiz_index" not in st.session_state:
    st.session_state.quiz_index = 0
if "quiz_score" not in st.session_state:
    st.session_state.quiz_score = 0
if "quiz_checked" not in st.session_state:
    st.session_state.quiz_checked = False
if "quiz_answer" not in st.session_state:
    st.session_state.quiz_answer = ""
if "unfamiliar_words" not in st.session_state:
    st.session_state.unfamiliar_words = set()
if "mastered_words" not in st.session_state:
    st.session_state.mastered_words = set()

with st.sidebar:
    st.subheader("👨‍👩‍👧 For Grown-Ups")
    st.markdown("Add a Gemini API key for extra word tips and meanings. Without a key, Chinese audio & local pinyin still work great!")
    api_key = st.text_input("Google Gemini API Key (optional)", type="password", value=get_api_key() or "")
    st.caption("🔊 Audio uses gTTS and needs an internet connection.")
    st.divider()
    st.markdown("💡 **Tip:** Type one word or phrase per line. Mix English & Chinese freely!")

st.subheader("📝 Step 1: Add your weekly words!")
with st.form("word_list_form"):
    raw = st.text_area("Type your list here:", value=st.session_state.raw_words, height=140, placeholder="beautiful\nfriend\n学校\n认真", label_visibility="collapsed")
    submitted = st.form_submit_button("🚀 Start My Practice!", type="primary")

if submitted:
    st.session_state.raw_words = raw
    st.session_state.quiz_words = normalize_words(raw)
    st.session_state.quiz_index = 0
    st.session_state.quiz_score = 0
    st.session_state.quiz_checked = False
    st.session_state.quiz_answer = ""
    st.session_state.unfamiliar_words = set()
    st.session_state.mastered_words = set()

words = normalize_words(st.session_state.raw_words)
if not words:
    st.info("👆 Enter a few words above and press 'Start My Practice' to begin!")
    st.stop()

if not st.session_state.quiz_words:
    st.session_state.quiz_words = words.copy()

key = api_key.strip() if api_key else get_api_key()
analysis = {}
error_detail = None

if key:
    with st.spinner("✨ Preparing your magic study notes..."):
        analysis, error_detail = get_analysis(words, key)

if error_detail and key:
    st.warning(f"Note: Full AI notes are limited right now ({error_detail}). Chinese pinyin is still provided!")

st.subheader("📖 Step 2: Let's learn our words!")

m_col1, m_col2 = st.columns(2)
with m_col1:
    st.markdown(f"🌟 **Mastered Words:** {len(st.session_state.mastered_words)}")
with m_col2:
    st.markdown(f"🔴 **Needs Practice:** {len(st.session_state.unfamiliar_words)}")

for index, word in enumerate(words):
    info = analysis.get(word, {})
    status_tag = ""
    if word in st.session_state.mastered_words:
        status_tag = " ✅ [Mastered]"
    elif word in st.session_state.unfamiliar_words:
        status_tag = " 🔴 [Needs Practice]"

    with st.expander(f"Word {index + 1}:  {word} {status_tag}", expanded=False):
        show_analysis(word, info)

st.divider()
st.subheader("🎯 Step 3: Dictation Time!")
st.write("Listen to the pronunciation or hint, then write or type your answer!")

active_quiz_words = st.session_state.quiz_words

if st.session_state.quiz_index >= len(active_quiz_words):
    st.balloons()
    st.success(f"🎉 Super job! You finished this practice set! Final Score: {st.session_state.quiz_score} / {len(active_quiz_words)}")
    
    col_reset, col_review = st.columns(2)
    if col_reset.button("🔄 Restart All Words", type="primary"):
        st.session_state.quiz_words = words.copy()
        st.session_state.quiz_index = 0
        st.session_state.quiz_score = 0
        st.session_state.quiz_checked = False
        st.session_state.quiz_answer = ""
        st.rerun()

    if st.session_state.unfamiliar_words and col_review.button(f"🔴 Practice Unfamiliar Only ({len(st.session_state.unfamiliar_words)})", type="secondary"):
        st.session_state.quiz_words = list(st.session_state.unfamiliar_words)
        st.session_state.quiz_index = 0
        st.session_state.quiz_score = 0
        st.session_state.quiz_checked = False
        st.session_state.quiz_answer = ""
        st.rerun()
else:
    idx = st.session_state.quiz_index
    target = active_quiz_words[idx]
    info = analysis.get(target, {})
    is_chinese = guess_language(target) == "Chinese"

    st.progress((idx) / len(active_quiz_words), text=f"⭐ Progress: Word {idx + 1} of {len(active_quiz_words)} | Score: {st.session_state.quiz_score}")
    
    with st.container(border=True):
        st.markdown(f"### ❓ Question {idx + 1}")
        q1, q2 = st.columns([1, 2])
        with q1:
            audio_button(target, str(info.get("language") or guess_language(target)), f"quiz-audio-{idx}")
            if is_chinese:
                st.caption(f"Pinyin: {info.get('pinyin') or local_pinyin(target)}")
        with q2:
            hint = info.get("meaning") or info.get("sentence") or "Listen closely to the audio!"
            st.markdown(f"💡 **Hint:** {hint}")
            
        if st.button("🔎 Show Extra Hint", key=f"hint-{idx}"):
            st.info(info.get("spelling_tip") or (f"Pinyin: {info.get('pinyin') or local_pinyin(target)}" if is_chinese else "Sound out the letters!"))
        
        # Fast canvas pad
        if is_chinese:
            st.markdown("✍️ **Write your characters on the magic pad:**")
            
            st_canvas(
                fill_color="rgba(255, 255, 255, 0)",
                stroke_width=4,
                stroke_color="#0284c7",
                background_color="#f8fafc",
                height=180,
                width=300,
                drawing_mode="freedraw",
                update_streamlit=False,
                key="canvas-fast-pad",
            )
            st.caption("👆 Use your finger or stylus to draw!")
            
            if not st.session_state.quiz_checked:
                if st.button("👁️ Check My Handwriting", type="primary", key=f"reveal-{idx}"):
                    st.session_state.quiz_checked = True
                    st.rerun()
        else:
            with st.form(f"quiz-form-{idx}"):
                answer = st.text_input("Type your answer here:", key=f"answer-input-{idx}", disabled=st.session_state.quiz_checked)
                check = st.form_submit_button("Check Answer ⭐", type="primary", disabled=st.session_state.quiz_checked)
            if check:
                st.session_state.quiz_answer = answer.strip()
                st.session_state.quiz_checked = True
                if st.session_state.quiz_answer.casefold() == target.casefold():
                    st.session_state.quiz_score += 1
                    st.session_state.mastered_words.add(target)
                    st.session_state.unfamiliar_words.discard(target)
                else:
                    st.session_state.unfamiliar_words.add(target)
                    st.session_state.mastered_words.discard(target)
                st.rerun()

        if st.session_state.quiz_checked:
            if is_chinese:
                st.info(f"✨ Correct Character: **{target}**")
                st.markdown("**Compare your strokes with the animation:**")
                render_hanzi_animations(target)
                
                col_yes, col_no = st.columns(2)
                if col_yes.button("I got it right! ✅", key=f"self-correct-{idx}"):
                    st.session_state.quiz_score += 1
                    st.session_state.mastered_words.add(target)
                    st.session_state.unfamiliar_words.discard(target)
                    st.session_state.quiz_index += 1
                    st.session_state.quiz_checked = False
                    st.rerun()
                if col_no.button("Need more practice ❌", key=f"self-wrong-{idx}"):
                    st.session_state.unfamiliar_words.add(target)
                    st.session_state.mastered_words.discard(target)
                    st.session_state.quiz_index += 1
                    st.session_state.quiz_checked = False
                    st.rerun()
            else:
                if st.session_state.quiz_answer.casefold() == target.casefold():
                    st.success("🎉 Correct! Fantastic job!")
                else:
                    st.error(f"Almost! The correct spelling is: **{target}**")
                if st.button("Next Word ➡️" if idx + 1 < len(active_quiz_words) else "Finish Quiz 🏆", type="primary", key=f"next-{idx}"):
                    st.session_state.quiz_index += 1
                    st.session_state.quiz_checked = False
                    st.session_state.quiz_answer = ""
                    st.rerun()

st.caption("🌈 Made with love for learning! Check official school textbooks for curriculum-specific stroke rules.")
