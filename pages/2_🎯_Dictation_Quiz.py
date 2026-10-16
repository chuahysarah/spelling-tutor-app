from __future__ import annotations

import re
import streamlit as st
import streamlit.components.v1 as components
from gtts import gTTS
from pypinyin import Style, pinyin
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="Dictation Quiz 🎯", page_icon="🎯", layout="centered")


def guess_language(text: str) -> str:
    return "Chinese" if re.search(r"[\u3400-\u9fff]", text) else "English"


def local_pinyin(text: str) -> str:
    return " ".join(part[0] for part in pinyin(text, style=Style.TONE, heteronym=False, errors=lambda x: list(x)))


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


st.title("🎯 Step 3: Dictation Quiz")

# Ensure all Session State keys are safely initialized across page switches
if "quiz_index" not in st.session_state:
    st.session_state.quiz_index = 0
if "quiz_score" not in st.session_state:
    st.session_state.quiz_score = 0
if "quiz_checked" not in st.session_state:
    st.session_state.quiz_checked = False
if "quiz_answer" not in st.session_state:
    st.session_state.quiz_answer = ""
if "mastered_words" not in st.session_state:
    st.session_state.mastered_words = set()
if "unfamiliar_words" not in st.session_state:
    st.session_state.unfamiliar_words = set()

raw_words = st.session_state.get("raw_words", "")
if not raw_words:
    st.info("👆 Please go to the Home page to add your spelling list first!")
    st.stop()

if "quiz_words" not in st.session_state or not st.session_state.quiz_words:
    st.session_state.quiz_words = [line.strip() for line in raw_words.replace("，", "\n").replace(",", "\n").splitlines() if line.strip()]

active_quiz_words = st.session_state.quiz_words
idx = st.session_state.quiz_index

if idx >= len(active_quiz_words):
    st.balloons()
    st.success(f"🎉 Quiz finished! Final Score: {st.session_state.quiz_score} / {len(active_quiz_words)}")
    if st.button("🔄 Restart Quiz", type="primary"):
        st.session_state.quiz_index = 0
        st.session_state.quiz_score = 0
        st.session_state.quiz_checked = False
        st.session_state.quiz_answer = ""
        st.rerun()
else:
    target = active_quiz_words[idx]
    is_chinese = guess_language(target) == "Chinese"

    st.progress(idx / len(active_quiz_words), text=f"⭐ Question {idx + 1} of {len(active_quiz_words)}")
    
    with st.container(border=True):
        st.markdown(f"### Question {idx + 1}")
        audio_button(target, "Chinese" if is_chinese else "English", f"quiz-aud-{idx}")
        if is_chinese:
            st.caption(f"Pinyin: {local_pinyin(target)}")

        # Chinese Handwriting Mode
        if is_chinese:
            st.markdown("✍️ **Write your answer:**")
            st_canvas(
                fill_color="rgba(255, 255, 255, 0)",
                stroke_width=4,
                stroke_color="#0284c7",
                background_color="#f8fafc",
                height=180,
                width=300,
                drawing_mode="freedraw",
                update_streamlit=False,
                key=f"canvas-pad-{idx}",
            )
            
            if not st.session_state.quiz_checked:
                if st.button("👁️ Check My Handwriting", type="primary", key=f"btn-check-{idx}"):
                    st.session_state.quiz_checked = True
                    st.rerun()
        
        # English Type-In Mode
        else:
            with st.form(f"quiz-form-{idx}"):
                answer = st.text_input("Type your answer:", disabled=st.session_state.quiz_checked)
                check_submitted = st.form_submit_button("Check Answer ⭐", type="primary", disabled=st.session_state.quiz_checked)
                
            if check_submitted:
                st.session_state.quiz_answer = answer.strip()
                st.session_state.quiz_checked = True
                if st.session_state.quiz_answer.casefold() == target.casefold():
                    st.session_state.quiz_score += 1
                st.rerun()

        # Revealed Answer & Self-Grading Area
        if st.session_state.quiz_checked:
            if is_chinese:
                st.info(f"✨ Correct Character: **{target}**")
                render_hanzi_animations(target)
                
                col_yes, col_no = st.columns(2)
                if col_yes.button("I got it right! ✅", key=f"btn-correct-{idx}"):
                    st.session_state.quiz_score += 1
                    st.session_state.mastered_words.add(target)
                    st.session_state.unfamiliar_words.discard(target)
                    st.session_state.quiz_index += 1
                    st.session_state.quiz_checked = False
                    st.rerun()
                if col_no.button("Need practice ❌", key=f"btn-wrong-{idx}"):
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
                    
                if st.button("Next Word ➡️", type="primary", key=f"btn-next-{idx}"):
                    st.session_state.quiz_index += 1
                    st.session_state.quiz_checked = False
                    st.session_state.quiz_answer = ""
                    st.rerun()
