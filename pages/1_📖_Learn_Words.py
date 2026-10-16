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

# Custom Memory Dict with 100% English Meanings, Chinese Sentences & Bilingual Tips
CHINESE_MEMORY_DICT = {
    "事情": {
        "meaning": "Things to do, matters, affairs, or tasks.",
        "sentence": "今天我有一件很重要的事情要完成。",
        "tip": "💡 Memory Trick: '情' has '忄' (heart) on the left! It means things you care about with your heart!"
    },
    "学校": {
        "meaning": "School — a place where students learn knowledge and play with friends.",
        "sentence": "我和朋友每天开心地上学校读书。",
        "tip": "💡 Memory Trick: Both '学' and '校' have '木' (wood) and roof radicals! Think of a wooden school building!"
    },
    "认真": {
        "meaning": "Serious, attentive, and focused on doing something carefully.",
        "sentence": "小明认真地听老师讲课和写作业。",
        "tip": "💡 Memory Trick: '认' has '讠' (words) — pay close attention to words when listening carefully!"
    },
    "爸爸": {
        "meaning": "Dad or father.",
        "sentence": "爸爸带我去公园骑脚踏车。",
        "tip": "💡 Memory Trick: Notice '父' (father radical) at the top of both characters!"
    },
    "妈妈": {
        "meaning": "Mom or mother.",
        "sentence": "妈妈准备了美味的晚餐。",
        "tip": "💡 Memory Trick: Look at the left side! It has '女' (woman) radical because Mom is a lady!"
    },
    "学习": {
        "meaning": "To study, learn, and practice new knowledge or skills.",
        "sentence": "我们要努力学习新知识。",
        "tip": "💡 Memory Trick: '学' has a roof radical '宀' at the top — learning under the school roof!"
    }
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
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=15, show_spinner=False)
def fetch_available_lists(child_name: str = "") -> dict[str, str]:
    if API_URL:
        try:
            params = {"action": "get_lists"}
            if child_name:
                params["child_name"] = child_name
            resp = requests.get(API_URL, params=params, allow_redirects=True, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
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
3. meaning: simple, fun, child-friendly definition.
   - FOR CHINESE WORDS: Write the definition 100% in simple English so primary school kids easily understand the word!
   - FOR ENGLISH WORDS: Write definition in simple English.
4. sentence: short, relatable daily life context sentence (written 100% in Simplified Chinese for Chinese words, English for English words).
5. spelling_tip: a super fun, child-friendly memory trick! 
   - For CHINESE: Use a playful mix of English and Chinese explaining radicals and components! (e.g., "'情' has '忄' (heart) on the left side!", "'休' is a person '人' leaning against a tree '木'!").
   - For ENGLISH: Use fun mnemonics or phonics rules in English.
6. pinyin: Chinese tone-marked pinyin or empty for English.

Items: """ + json.dumps(words, ensure_ascii=False)
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}], 
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2}
    }
    
    clean_token = api_key.strip().strip("'").strip('"')
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={clean_token}"

    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=8)
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
        edited_name = st.text_input("New Name:", value=active_child, key=f"p1_rename_input_{active_child}")
        if st.button("Save New Name", type="primary", use_container_width=True):
            clean_rename = edited_name.strip()
            if clean_rename and clean_rename != active_child:
                rename_child_profile(active_child, clean_rename)
                st.success(f"Renamed to {clean_rename}!")
                st.rerun()

active_child = st.session_state.active_child

st.title(f"📖 Hi {active_child}! Let's Learn Our Words!")

available_lists = fetch_available_lists(active_child)
list_titles = list(available_lists.keys())

if not list_titles:
    st.info(f"📚 No spelling lists assigned to {active_child} yet. Grown-ups can add lists on the home page!")
    st.stop()

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
    st.warning(f"⚠️ No words found in this list for {active_child}.")
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
            preset = CHINESE_MEMORY_DICT.get(word, {})
            py = str(info.get("pinyin") or local_pinyin(word))
            meaning = info.get('meaning') or preset.get('meaning') or f"Chinese word / 词语: {word}"
            sentence = info.get("sentence") or preset.get('sentence') or f"今天我们要学习 '{word}' 这个词。"
            
            default_tip = f"Notice the structure of '{word}'! Practice the stroke order step-by-step!"
            tip = info.get('spelling_tip') or preset.get('tip') or default_tip

            st.write(f"🗣️ **Pinyin:** `{py}`")
            st.write("✍️ **Stroke Order Animation:**")
            render_hanzi_animations(word)
            st.write(f"💡 **Meaning:** {meaning}")
            st.write(f"💬 **Example:** {sentence}")
            if sentence:
                audio_button(sentence, "Chinese", f"sentence-{word}")
            st.write(f"⭐ **Fun Memory Tip (记忆小贴士):** {tip}")
