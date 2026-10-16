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

st.set_page_config(
    page_title="Learn Words 📖",
    page_icon="📖",
    layout="centered",
    initial_sidebar_state="expanded"
)

API_URL = st.secrets.get("GSHEETS_API_URL", "").strip()
ANALYSIS_SCHEMA_VERSION = 3

CHINESE_MEMORY_DICT = {
    "事情": {
        "meaning": "Things to do, matters, affairs, or tasks.",
        "sentence": "今天我有一件很重要的事情要完成。",
        "tip": "💡 Memory Trick: '情' has '忄' (heart) on the left! It means things you care about with your heart!"
    },
    "学校": {
        "meaning": "School — a place where students learn knowledge and play with friends.",
        "sentence": "我每天开心地去学校和朋友一起读书。",
        "tip": "💡 Memory Trick: Both '学' and '校' have '木' (wood) and roof radicals! Think of a wooden school building!"
    },
    "认真": {
        "meaning": "Serious, attentive, and focused on doing something carefully.",
        "sentence": "小明认真地听老师讲课，也认真地写作业。",
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
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700&display=swap');
:root { --ink:#26324b; --blue:#2864dc; --purple:#7652d6; --coral:#ff765e; --sun:#ffc94a; --mint:#36bca0; --sky:#e7f5ff; }
html, body, [class*="css"], button, input, select, textarea {
    font-family:'Fredoka',sans-serif !important; color:var(--ink);
}
html, body, [data-testid="stAppViewContainer"] { background:#fffaf0 !important; }
[data-testid="stHeader"] { background:rgba(255,250,240,.88) !important; }
[data-testid="stMainBlockContainer"] { max-width:1100px; padding-top:2rem; }
h1 { color:#3158b8 !important; font-weight:700 !important; letter-spacing:-.035em; }
h2 { color:#6746bd !important; font-weight:700 !important; }
h3 { color:#168d7c !important; font-weight:700 !important; }
.stButton > button {
    min-height:3.2rem; border:0 !important; border-radius:18px !important;
    background:linear-gradient(115deg,#ff795e 0%,#ff9f54 100%) !important;
    color:#fff !important; font-size:1.16rem !important; font-weight:700 !important;
    padding:.65rem 1.25rem !important; box-shadow:0 5px 0 #df624b,0 9px 18px rgba(223,98,75,.16) !important;
    transition:transform .16s ease,box-shadow .16s ease,filter .16s ease;
}
.stButton > button:hover { transform:translateY(-2px); filter:saturate(1.12); box-shadow:0 7px 0 #df624b,0 12px 22px rgba(223,98,75,.2) !important; }
.stButton > button:active { transform:translateY(2px); box-shadow:0 2px 0 #df624b !important; }
.stButton > button:focus-visible, input:focus-visible, textarea:focus-visible { outline:3px solid #3158b8 !important; outline-offset:3px; }
[data-testid="stSidebar"] {
    background:linear-gradient(165deg,#e6f4ff 0%,#f0eaff 55%,#fff0e8 100%) !important;
    border-right:3px solid #d6e5ff !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#34415c; }
[data-testid="stSidebarCollapseButton"] button {
    background:linear-gradient(135deg,#ffd34f,#ffad52) !important; color:#26324b !important;
    border:2px solid #efa83a !important; border-radius:12px !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background:#fff !important; border:2px solid #b8d9ff !important; border-radius:16px !important;
}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stSelectbox"] > div > div {
    border-radius:14px !important; border-color:#bdd8fa !important; background:#fff !important;
}
[data-testid="stExpander"] {
    background:rgba(255,255,255,.88); border:2px solid #e5dcfb !important; border-radius:18px !important;
}
[data-testid="stAlert"] { border-radius:16px !important; }
hr { border-color:#e6ddf7 !important; }
.hero {
    position:relative; overflow:hidden; padding:2.4rem 1.8rem; border-radius:30px;
    background:linear-gradient(125deg,#fff0ae 0%,#ffdfd7 48%,#d9eeff 100%);
    border:3px solid #fff; text-align:center; margin:0 0 1.7rem;
    box-shadow:0 12px 30px rgba(62,83,132,.12),inset 0 0 0 2px rgba(255,198,76,.6);
}
.hero h1 { color:#3158b8 !important; margin-bottom:.55rem; font-size:2.5rem !important; }
.hero p { color:#39445d; font-size:1.2rem; margin:0; }
.action-card {
    padding:1.45rem 1.2rem; min-height:155px; border-radius:24px;
    border:2px solid #fff; text-align:center;
    background:linear-gradient(145deg,#fff 0%,#eff8ff 100%);
    box-shadow:0 8px 22px rgba(53,86,144,.11),inset 0 0 0 2px #cde5ff;
}
.action-card h3 { font-size:1.65rem; color:#3158b8; margin-bottom:.4rem; }
.action-card p { font-size:1.05rem; color:#4b5872; }
@media (max-width:640px) {
    [data-testid="stMainBlockContainer"] { padding:1.1rem 1rem 2rem; }
    .hero { padding:1.6rem 1rem; border-radius:22px; }
    .hero h1 { font-size:2rem !important; }
}
@media (prefers-reduced-motion:reduce) { *,*::before,*::after { scroll-behavior:auto !important; transition:none !important; animation:none !important; } }
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


def contains_chinese(text: object) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", str(text or "")))


def is_valid_english_meaning(text: object) -> bool:
    value = str(text or "").strip()
    return bool(re.search(r"[A-Za-z]", value)) and not contains_chinese(value)


def is_valid_chinese_example(text: object, target: str) -> bool:
    value = str(text or "").strip()
    normalized_value = re.sub(r"\s+", "", value)
    normalized_target = re.sub(r"\s+", "", target.strip())
    return (
        contains_chinese(value)
        and bool(normalized_target)
        and normalized_target in normalized_value
        and value[-1:] in {"。", "！", "？", ".", "!", "?"}
    )


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
    
    prompt = """You are an expert, careful Mandarin Chinese and English tutor for children aged 7-9. Analyze every item below. Return ONLY a JSON object keyed by the exact input item.

For each item, provide:
1. language: 'English' or 'Chinese'
2. syllables: English syllables with hyphens; for Chinese give tone-marked pinyin.
3. meaning: For EVERY Chinese input item—single characters, words, phrases, or full sentences—explain its meaning entirely in simple English. Never include Chinese characters in this field. If the input is a full sentence, explain the whole sentence in natural English. For English inputs, define it in simple English.
4. sentence: For a Chinese input, write one grammatically natural, complete Simplified Chinese sentence that uses the exact input item naturally and meaningfully. Include the exact input text unchanged and end with Chinese sentence punctuation. For a single Chinese character, use it naturally within a common word. If the input itself is already a complete sentence, use that sentence as the example rather than inserting it awkwardly into another sentence. Do not output a fragment, word list, translation, or explanation as the example. For English inputs, write one natural English sentence using the exact input.
5. spelling_tip: a super fun, child-friendly memory trick!
   - For CHINESE: Use a playful mix of English and Chinese explaining radicals and components.
   - For ENGLISH: Use fun mnemonics or phonics rules in English.
6. pinyin: Chinese tone-marked pinyin or empty for English.
Do not add fields other than the six listed above. Check that each Chinese meaning is entirely English and each example is a complete, natural sentence that uses its target.

Items: """ + json.dumps(words, ensure_ascii=False)
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}], 
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.0}
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

    for key_prefix in ["active_week", "raw_words", "cached_analysis", "cached_analysis_version", "quiz_index", "quiz_score", "quiz_checked", "quiz_logged", "quiz_result", "mastered_words", "unfamiliar_words"]:
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
    st.session_state[f"cached_analysis_version_{active_child}"] = 0
    st.rerun()

raw_words = st.session_state.get(f"raw_words_{active_child}", "")
words = [line.strip() for line in raw_words.replace("，", "\n").replace(",", "\n").splitlines() if line.strip()]

if not words:
    st.warning(f"⚠️ No words found in this list for {active_child}.")
    st.stop()

if f"cached_analysis_{active_child}" not in st.session_state:
    st.session_state[f"cached_analysis_{active_child}"] = {}

key = get_api_key()

analysis_version_key = f"cached_analysis_version_{active_child}"
if key and words and (
    not st.session_state.get(f"cached_analysis_{active_child}")
    or st.session_state.get(analysis_version_key, 0) < ANALYSIS_SCHEMA_VERSION
):
    with st.spinner(f"✨ Loading word details for {active_child}..."):
        data, err = get_analysis(words, key)
        if not err and data:
            st.session_state[f"cached_analysis_{active_child}"] = data
            st.session_state[analysis_version_key] = ANALYSIS_SCHEMA_VERSION

analysis = st.session_state.get(f"cached_analysis_{active_child}", {})

for index, word in enumerate(words):
    info = analysis.get(word, {})
    lang = guess_language(word)  # Do not trust the model to classify Chinese targets.
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
            candidate_meaning = info.get("meaning")
            if is_valid_english_meaning(candidate_meaning):
                meaning = str(candidate_meaning).strip()
            elif is_valid_english_meaning(preset.get("meaning")):
                meaning = str(preset["meaning"]).strip()
            else:
                meaning = "The English meaning for this item is not available yet. Please ask a grown-up to refresh the word details."

            candidate_sentence = info.get("sentence")
            if is_valid_chinese_example(candidate_sentence, word):
                sentence = str(candidate_sentence).strip()
            elif is_valid_chinese_example(preset.get("sentence"), word):
                sentence = str(preset["sentence"]).strip()
            else:
                sentence = ""
            
            default_tip = f"Notice the structure of '{word}'! Practice the stroke order step-by-step!"
            tip = info.get('spelling_tip') or preset.get('tip') or default_tip

            st.write(f"🗣️ **Pinyin:** `{py}`")
            st.write("✍️ **Stroke Order Animation:**")
            render_hanzi_animations(word)
            st.write(f"💡 **Meaning:** {meaning}")
            if sentence:
                st.write(f"💬 **Example:** {sentence}")
            else:
                st.caption("A natural example sentence could not be generated. Ask a grown-up to refresh the word details.")
            if sentence:
                audio_button(sentence, "Chinese", f"sentence-{word}")
            st.write(f"⭐ **Fun Memory Tip (记忆小贴士):** {tip}")
