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

st.set_page_config(page_title="Weekly Spelling Practice", page_icon="✏️", layout="centered")

st.markdown("""
<style>
.block-container {max-width: 900px; padding-top: 2rem; padding-bottom: 3rem;}
.hero {padding: 1.35rem 1.5rem; border-radius: 18px; background: linear-gradient(120deg,#eff6ff,#f0fdf4); margin-bottom: 1rem;}
.hero h1 {margin: 0 0 .35rem 0; color: #17365d;}
.word-card {padding: 1rem 1.2rem; border: 1px solid #e2e8f0; border-radius: 14px; background: #fff; margin: .5rem 0;}
.small-note {color: #64748b; font-size: .9rem;}
</style>
<div class="hero"><h1>✏️ Weekly Spelling Practice</h1><div>Listen, learn, and practise your English and Chinese words.</div></div>
""", unsafe_allow_html=True)

st.caption("A friendly practice space for 听写 / 默写. Add your weekly list, explore each word, then try a quiz!")


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


def get_available_models(api_key: str) -> list[str]:
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        resp = requests.get(url, timeout=10)
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
            resp = requests.post(url, json=payload, timeout=20)
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


@st.cache_data(show_spinner=False, max_entries=128)
def make_audio(text: str, lang: str) -> bytes:
    from io import BytesIO
    audio = BytesIO()
    gTTS(text=text, lang=lang, slow=False).write_to_fp(audio)
    return audio.getvalue()


def audio_button(text: str, language: str, key: str) -> None:
    lang = "zh-CN" if language == "Chinese" else "en"
    try:
        st.audio(make_audio(text, lang), format="audio/mp3")
    except Exception as exc:
        st.info(f"Audio could not be loaded right now. Please check your internet connection. ({type(exc).__name__})")


def render_hanzi_animations(word: str) -> None:
    chinese_chars = [char for char in word if re.search(r"[\u3400-\u9fff]", char)]
    if not chinese_chars:
        return

    targets = ""
    scripts = ""
    
    for i, char in enumerate(chinese_chars):
        div_id = f"target-{i}-{ord(char)}"
        targets += f'<div id="{div_id}" style="display:inline-block; margin: 5px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fafafa;"></div>'
        scripts += f"""
        HanziWriter.create('{div_id}', '{char}', {{
            width: 110,
            height: 110,
            padding: 5,
            showOutline: true,
            strokeAnimationSpeed: 1,
            delayBetweenStrokes: 150
        }}).loopCharacterAnimation();
        """

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <script src="https://cdn.jsdelivr.net/npm/hanzi-writer@3.5/dist/hanzi-writer.min.js"></script>
    </head>
    <body style="margin: 0; padding: 0; background: transparent;">
      <div style="display: flex; flex-wrap: wrap; gap: 8px;">
        {targets}
      </div>
      <script>
        {scripts}
      </script>
    </body>
    </html>
    """
    components.html(html_code, height=130)


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
    st.markdown(f'<div class="word-card"><h3 style="margin:0">{word}</h3></div>', unsafe_allow_html=True)
    audio_button(word, language, f"audio-{word}")
    
    if language == "English":
        cols = st.columns(2)
        cols[0].markdown(f"**Syllables:** {info.get('syllables', '—')}")
        cols[1].markdown(f"**Meaning:** {info.get('meaning', '—')}")
        st.markdown(f"**Example:** {info.get('sentence', '—')}")
        st.markdown(f"**Spelling tip:** {info.get('spelling_tip', '—')}")
    else:
        py = str(info.get("pinyin") or local_pinyin(word))
        st.markdown(f"**拼音 Pinyin:** {py}")
        if py:
            st.caption("Listen to the Chinese word and its pronunciation:")
            audio_button(py, "Chinese", f"pinyin-{word}")
            
        st.markdown("**笔顺动画 Visual Stroke Order:**")
        render_hanzi_animations(word)

        st.markdown(f"**意思 Meaning:** {info.get('meaning', '—')}")
        st.markdown(f"**例句 Example:** {info.get('sentence', '—')}")
        st.markdown(f"**总笔画 Stroke count:** {info.get('stroke_count') or 'Please verify with your class dictionary'}")
        st.markdown(f"**部首 Radical:** {info.get('radical') or 'Please verify with your class dictionary'}")
        st.markdown(f"**结构 Structure:** {info.get('structure') or '—'}")
        
        strokes = info.get("strokes")
        if strokes:
            st.markdown(f"**笔顺名称 Stroke names:** {format_strokes(strokes)}")
            
        st.markdown(f"**记忆小贴士 Tip:** {info.get('spelling_tip', '—')}")
        st.caption("Stroke details are AI-generated study hints; check your textbook or teacher for required stroke order.")


if "raw_words" not in st.session_state:
    st.session_state.raw_words = ""
if "quiz_index" not in st.session_state:
    st.session_state.quiz_index = 0
if "quiz_score" not in st.session_state:
    st.session_state.quiz_score = 0
if "quiz_checked" not in st.session_state:
    st.session_state.quiz_checked = False
if "quiz_answer" not in st.session_state:
    st.session_state.quiz_answer = ""

with st.sidebar:
    st.subheader("For grown-ups")
    st.markdown("Add a Gemini API key for word-by-word explanations. Without one, Chinese pinyin still works, but detailed explanations are limited.")
    api_key = st.text_input("Google Gemini API key (optional)", type="password", value=get_api_key() or "", help="Stored only for this session unless configured in Streamlit secrets.")
    st.caption("Audio uses gTTS and needs an internet connection.")
    st.divider()
    st.markdown("**Tip:** One word or phrase per line. English, 中文, or a mix are welcome.")

st.subheader("1. Add this week's words")
with st.form("word_list_form"):
    raw = st.text_area("Your spelling list", value=st.session_state.raw_words, height=150, placeholder="beautiful\nfriend\n学校\n认真", label_visibility="collapsed")
    submitted = st.form_submit_button("Save my list", type="primary")
if submitted:
    st.session_state.raw_words = raw
    st.session_state.quiz_index = 0
    st.session_state.quiz_score = 0
    st.session_state.quiz_checked = False
    st.session_state.quiz_answer = ""

words = normalize_words(st.session_state.raw_words)
if not words:
    st.info("Enter a few words above to get started.")
    st.stop()

key = api_key.strip() if api_key else get_api_key()
analysis = {}
error_detail = None

if key:
    with st.spinner("Preparing your word notes…"):
        analysis, error_detail = get_analysis(words, key)

if error_detail and key:
    st.warning(f"Gemini analysis is currently limited. Details: `{error_detail}`. Chinese pinyin is still provided locally.")

st.subheader("2. Learn about each word")
for index, word in enumerate(words):
    info = analysis.get(word, {})
    with st.expander(f"{index + 1}. {word} · {guess_language(word)}", expanded=False):
        show_analysis(word, info)

st.divider()
st.subheader("3. Dictation quiz")
st.write("Listen or read a hint, then write/type your answer without looking.")
if st.session_state.quiz_index >= len(words):
    st.success(f"Great work! You finished the list. Score: {st.session_state.quiz_score} / {len(words)}")
    if st.button("Try again", type="primary"):
        st.session_state.quiz_index = 0
        st.session_state.quiz_score = 0
        st.session_state.quiz_checked = False
        st.session_state.quiz_answer = ""
        st.rerun()
else:
    idx = st.session_state.quiz_index
    target = words[idx]
    info = analysis.get(target, {})
    is_chinese = guess_language(target) == "Chinese"

    st.progress(idx / len(words), text=f"Word {idx + 1} of {len(words)} · Score {st.session_state.quiz_score}")
    with st.container(border=True):
        st.markdown(f"### Word {idx + 1}")
        q1, q2 = st.columns([1, 2])
        with q1:
            audio_button(target, str(info.get("language") or guess_language(target)), f"quiz-audio-{idx}")
            if is_chinese:
                st.caption(f"Pinyin: {info.get('pinyin') or local_pinyin(target)}")
        with q2:
            hint = info.get("meaning") or info.get("sentence") or "Listen carefully and remember your word."
            st.markdown(f"**Hint:** {hint}")
            
        if st.button("Show another hint", key=f"hint-{idx}"):
            st.info(info.get("spelling_tip") or (f"Pinyin: {info.get('pinyin') or local_pinyin(target)}" if is_chinese else "Think about the sounds and syllables."))
        
        # Chinese Handwritten Pad with update_streamlit=False to prevent WebSocket lag
        if is_chinese:
            st.markdown("✍️ **Write the Chinese characters on the writing pad below:**")
            
            st_canvas(
                fill_color="rgba(255, 255, 255, 0)",
                stroke_width=4,
                stroke_color="#0f172a",
                background_color="#f8fafc",
                height=200,
                width=320,
                drawing_mode="freedraw",
                update_streamlit=False,  # Prevents lagging/hanging on every stroke
                key=f"canvas-{idx}",
            )
            st.caption("Use your finger or stylus to write on the grid.")
            
            if not st.session_state.quiz_checked:
                if st.button("Check my handwriting 👁️", type="primary", key=f"reveal-{idx}"):
                    st.session_state.quiz_checked = True
                    st.rerun()
        else:
            with st.form(f"quiz-form-{idx}"):
                answer = st.text_input("Type your answer", key=f"answer-input-{idx}", disabled=st.session_state.quiz_checked)
                check = st.form_submit_button("Check answer", type="primary", disabled=st.session_state.quiz_checked)
            if check:
                st.session_state.quiz_answer = answer.strip()
                st.session_state.quiz_checked = True
                if st.session_state.quiz_answer.casefold() == target.casefold():
                    st.session_state.quiz_score += 1
                st.rerun()

        if st.session_state.quiz_checked:
            if is_chinese:
                st.info(f"Correct Character: **{target}**")
                st.markdown("**Compare your strokes with the correct order:**")
                render_hanzi_animations(target)
                
                col_yes, col_no = st.columns(2)
                if col_yes.button("I wrote it correctly! ✅", key=f"self-correct-{idx}"):
                    st.session_state.quiz_score += 1
                    st.session_state.quiz_index += 1
                    st.session_state.quiz_checked = False
                    st.rerun()
                if col_no.button("I need more practice ❌", key=f"self-wrong-{idx}"):
                    st.session_state.quiz_index += 1
                    st.session_state.quiz_checked = False
                    st.rerun()
            else:
                if st.session_state.quiz_answer.casefold() == target.casefold():
                    st.success("Correct! Well done!")
                else:
                    st.error(f"Not quite. The answer is: **{target}**")
                if st.button("Next word →" if idx + 1 < len(words) else "Finish quiz", type="primary", key=f"next-{idx}"):
                    st.session_state.quiz_index += 1
                    st.session_state.quiz_checked = False
                    st.session_state.quiz_answer = ""
                    st.rerun()

st.caption("Made for learning. Chinese stroke counts and radicals may vary by dictionary or curriculum; please confirm important details with a trusted class resource.")
