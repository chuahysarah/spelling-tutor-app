from __future__ import annotations

import json
import os
import re
from typing import Any
from html import escape

import requests
import streamlit as st
import streamlit.components.v1 as components
from gtts import gTTS
from pypinyin import Style, pinyin

st.set_page_config(
    page_title="Learn Words 📖",
    page_icon="📖",
    layout="centered",
    initial_sidebar_state="auto"
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
/* Visual theme only: no changes to word processing, audio, or Hanzi Writer logic. */
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700;800&family=Nunito:wght@400;500;600;700;800&display=swap');

:root {
    --ink:#111827; --body:#1f2937; --blue:#173f91; --blue-dark:#12336f;
    --purple:#4b1d82; --sun:#ffc94a; --cream:#fffefa;
    --surface:#ffffff; --focus:#ffc000; --control-border:#64748b;
}
html, body, [data-testid="stAppViewContainer"],
[data-testid="stMarkdownContainer"], button, input, textarea, select {
    font-family:'Nunito','Trebuchet MS',Arial,sans-serif !important;
}
[data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background:var(--cream) !important;
    color:var(--ink) !important;
}
[data-testid="stHeader"] { background:var(--cream) !important; }
[data-testid="stMainBlockContainer"] { max-width:1100px; padding:2rem 1rem; }

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
    font-family:'Nunito','Trebuchet MS',Arial,sans-serif !important;
    color:var(--body) !important;
    font-size:1.125rem; font-weight:500; line-height:1.5;
}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
    color:var(--body) !important; opacity:1 !important;
    font-size:1rem !important;
}
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {
    font-family:'Baloo 2','Trebuchet MS',sans-serif !important;
    font-weight:800 !important; line-height:1.25;
}
[data-testid="stMarkdownContainer"] h1 { color:var(--blue) !important; font-size:2rem !important; }
[data-testid="stMarkdownContainer"] h2 { color:var(--purple) !important; font-size:1.625rem !important; }
[data-testid="stMarkdownContainer"] h3 { color:#07594f !important; font-size:1.375rem !important; }
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label {
    color:var(--ink) !important; font-family:'Nunito','Trebuchet MS',Arial,sans-serif !important;
    font-size:1.125rem !important; font-weight:700 !important;
}

.hero {
    padding:2rem 1.5rem; border-radius:30px; margin:0 0 1.5rem;
    background:linear-gradient(125deg,#fff0ae 0%,#ffdfd7 48%,#d9eeff 100%);
    border:2px solid #c6a14e; text-align:center;
    box-shadow:0 12px 30px rgba(62,83,132,.12);
}
[data-testid="stMarkdownContainer"] .hero h1 {
    font-size:2.5rem !important; line-height:1.25; margin:0;
}
.child-name {
    display:inline-block; max-width:100%; overflow-wrap:anywhere;
    margin:0 .08em; padding:0 .32em; border-radius:.38em;
    background:#ffc94a; color:#111827 !important;
    font-weight:800; box-shadow:0 3px 0 #6b4e00;
    transform-origin:center;
    animation:child-name-pop .5s cubic-bezier(.2,.8,.2,1) both;
}
@keyframes child-name-pop {
    0% { transform:translateY(.2em) scale(.9); }
    70% { transform:translateY(-.04em) scale(1.04); }
    100% { transform:translateY(0) scale(1); }
}

/* Text and labels inside a Streamlit button need their own color rule.
   Setting only button{color:white} can leave nested Markdown text dark. */
[data-testid="stButton"] button,
[data-testid="stFormSubmitButton"] button {
    min-height:48px; padding:.65rem 1.15rem !important;
    border-radius:16px !important; border:2px solid var(--blue) !important;
    background:var(--blue) !important; color:#ffffff !important;
    font-size:1.125rem !important; font-weight:700 !important;
    white-space:normal;
    transition:transform .15s ease,box-shadow .15s ease;
}
[data-testid="stButton"] button p,
[data-testid="stButton"] button span,
[data-testid="stFormSubmitButton"] button p,
[data-testid="stFormSubmitButton"] button span {
    color:#ffffff !important;
    font-family:'Nunito','Trebuchet MS',Arial,sans-serif !important;
    font-size:1.125rem !important; font-weight:700 !important;
}
[data-testid="stButton"] button:hover,
[data-testid="stFormSubmitButton"] button:hover {
    background:var(--blue-dark) !important; transform:translateY(-2px);
    box-shadow:0 6px 14px rgba(23,63,145,.18);
}
[data-testid="stButton"] button:active { transform:scale(.985); }

[data-testid="stSidebar"] {
    background:linear-gradient(165deg,#e6f4ff 0%,#f0eaff 55%,#fff0e8 100%) !important;
    border-right:3px solid #d6e5ff !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:var(--body) !important; }
[data-testid="stSidebarCollapseButton"] button {
    min-width:48px; min-height:48px; border-radius:12px !important;
    background:#ffc94a !important; color:var(--ink) !important;
    border:2px solid #6b4e00 !important;
}
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="collapsedControl"] button,
button[data-testid="stSidebarCollapsedControl"],
button[data-testid="collapsedControl"] {
    display:flex !important; align-items:center !important; justify-content:center !important;
    gap:.5rem !important; min-width:8.25rem !important; min-height:3rem !important;
    padding:.55rem .8rem !important; border-radius:14px !important;
    border:2px solid #ffc000 !important; background:#173f91 !important;
    color:#ffffff !important; cursor:pointer;
    box-shadow:0 3px 0 #12336f,0 5px 12px rgba(17,24,39,.2);
}
[data-testid="stSidebarCollapsedControl"] button::after,
[data-testid="collapsedControl"] button::after,
button[data-testid="stSidebarCollapsedControl"]::after,
button[data-testid="collapsedControl"]::after {
    content:"Open menu"; color:#ffffff;
    font:700 1rem 'Nunito','Trebuchet MS',Arial,sans-serif;
    white-space:nowrap;
}
[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="collapsedControl"] svg {
    width:1.25rem !important; height:1.25rem !important; color:white !important;
}

[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background:#ffffff !important; color:var(--ink) !important;
    border:2px solid var(--control-border) !important;
    border-radius:14px !important; min-height:48px;
    font-size:1.125rem !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] input {
    color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] [role="combobox"] {
    color:var(--ink) !important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder { color:#374151 !important; opacity:1; }
[role="listbox"] { background:#ffffff !important; color:#111827 !important; }
[role="option"] { color:#111827 !important; }

/* Word panels: subtle pastel surfaces with dark text. */
[data-testid="stExpander"] {
    border:2px solid #64748b !important; border-radius:18px !important;
    background:#ffffff !important; margin-bottom:.75rem;
    box-shadow:0 5px 14px rgba(53,86,144,.08);
}
[data-testid="stExpander"] summary {
    min-height:48px; border-radius:16px;
    background:#f0eaff !important; color:#111827 !important;
}
[data-testid="stExpander"] summary p {
    color:#173f91 !important; font-size:1.3rem !important;
    font-family:'Baloo 2','Trebuchet MS',sans-serif !important;
    font-weight:800 !important; overflow-wrap:anywhere;
}
[data-testid="stExpander"] summary:hover { background:#e6e0fb !important; }
[data-testid="stExpanderDetails"] { padding:1rem !important; }
[data-testid="stMain"] [data-testid="stExpander"] {
    animation:word-panel-rise .35s ease-out both;
}
@keyframes word-panel-rise {
    from { transform:translateY(6px); }
    to { transform:translateY(0); }
}
[data-testid="stMarkdownContainer"] code {
    color:#4b1d82 !important; background:#f0eaff !important;
    font-size:1.0625rem; overflow-wrap:anywhere;
}
[data-testid="stAudio"] { width:100%; max-width:100%; margin:.35rem 0 .75rem; }
[data-testid="stAlert"] { background:#eff6ff !important; border-radius:16px !important; color:#111827 !important; }
hr { border-color:#e6ddf7 !important; }

/* Keep Previous and Next together, including on small touch screens. */
.st-key-learn_item_navigation [data-testid="stHorizontalBlock"] {
    flex-direction:row !important; flex-wrap:nowrap !important; gap:.75rem !important;
}
.st-key-learn_item_navigation [data-testid="stColumn"] {
    flex:1 1 0 !important; min-width:0 !important; width:auto !important;
}
.item-progress {
    text-align:center; color:#173f91 !important;
    font-family:'Baloo 2','Trebuchet MS',sans-serif !important;
    font-size:1.3rem; font-weight:800; margin:.75rem 0;
}
[data-testid="stButton"] button:disabled {
    background:#e5e7eb !important; border-color:#64748b !important;
    color:#374151 !important; opacity:1 !important;
    transform:none !important; box-shadow:none !important; cursor:default;
}
[data-testid="stButton"] button:disabled p,
[data-testid="stButton"] button:disabled span { color:#374151 !important; }

/* Keep the original native interactions and focus behavior. */
button:focus-visible, input:focus-visible, textarea:focus-visible,
select:focus-visible, a:focus-visible, summary:focus-visible, [tabindex]:focus-visible {
    outline:3px solid #ffc000 !important; outline-offset:3px !important;
    box-shadow:0 0 0 2px #111827 !important;
}
@media (max-width:640px) {
    [data-testid="stMainBlockContainer"] { padding:.75rem .75rem 1.5rem; }
    .hero { padding:1.25rem 1rem; border-radius:20px; margin-bottom:1rem; }
    [data-testid="stMarkdownContainer"] .hero h1 {
        font-size:clamp(1.6rem,7vw,2rem) !important;
    }
    .child-name { padding:0 .24em; }
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li { font-size:1.0625rem; line-height:1.45; }
    [data-testid="stButton"] button { width:100%; min-height:48px; }
    [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
    [data-testid="stSelectbox"] [role="combobox"] { min-height:48px; font-size:18px !important; }
    [data-testid="stExpanderDetails"] { padding:.75rem !important; }
}
@media (prefers-reduced-motion:reduce) {
    *,*::before,*::after {
        scroll-behavior:auto !important; transition:none !important;
        animation:none !important; transform:none !important;
    }
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

    html_code = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/hanzi-writer@3.5/dist/hanzi-writer.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@500;600;700;800&display=swap');
* { box-sizing:border-box; }
body { margin:0; padding:4px; background:transparent; color:#111827; font:600 16px/1.4 'Nunito',Arial,sans-serif; }
.instructions { margin:0 0 10px; }
.cards { display:flex; flex-wrap:wrap; gap:12px; justify-content:center; align-items:flex-start; }
.stroke-card { width:192px; padding:8px; border:2px solid #64748b; border-radius:16px; background:#fff; }
.character-label { margin:0 0 4px; text-align:center; font-size:22px; font-weight:800; }
.character-stage { position:relative; width:172px; height:172px; }
.character-target { width:172px; height:172px; }
.number-layer { position:absolute; inset:0; width:172px; height:172px; pointer-events:none; }
.number-layer[hidden] { display:none; }
.stroke-number text { fill:#111827; font:800 11px Arial,sans-serif; text-anchor:middle; dominant-baseline:central; }
.stroke-number circle { fill:#ffc94a; stroke:#111827; stroke-width:1.5; }
.leader { stroke:#475569; stroke-width:1; }
label { display:flex; align-items:center; gap:8px; min-height:48px; cursor:pointer; font-size:14px; }
input[type="checkbox"] { width:22px; height:22px; accent-color:#173f91; }
button { width:100%; min-height:48px; border:2px solid #173f91; border-radius:10px; background:#173f91; color:white; font:800 16px 'Nunito',Arial,sans-serif; cursor:pointer; }
button:disabled { color:#374151; background:#e5e7eb; border-color:#64748b; cursor:default; }
button:focus-visible, input:focus-visible { outline:3px solid #ffc000; outline-offset:2px; box-shadow:0 0 0 2px #111827; }
.status { margin:6px 0; min-height:20px; text-align:center; color:#374151; font-size:13px; }
.error { color:#8e1b10; }
</style>
</head>
<body>
<p class="instructions">Numbers show the order of strokes. Each label points to where a stroke starts.</p>
<div class="cards" id="stroke-cards"></div>
<script>
(() => {
    const characters = __CHARACTERS__;
    const SIZE = 172;
    const PADDING = 12;
    const SVG_NS = 'http://www.w3.org/2000/svg';
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function svgElement(tag, attrs) {
        const node = document.createElementNS(SVG_NS, tag);
        for (const [key, value] of Object.entries(attrs || {})) node.setAttribute(key, value);
        return node;
    }

    // Spread overlapping badges slightly, with leader lines back to exact starts.
    function placeBadge(start, used) {
        for (let attempt = 0; attempt < 100; attempt++) {
            const radius = attempt === 0 ? 0 : 3 * Math.sqrt(attempt);
            const angle = attempt * 2.39996323;
            const candidate = {
                x: Math.min(SIZE - 11, Math.max(11, start.x + radius * Math.cos(angle))),
                y: Math.min(SIZE - 11, Math.max(11, start.y + radius * Math.sin(angle)))
            };
            if (used.every(p => Math.hypot(p.x - candidate.x, p.y - candidate.y) >= 21)) {
                used.push(candidate);
                return candidate;
            }
        }
        const fallback = { x:Math.min(SIZE - 11, Math.max(11, start.x)), y:Math.min(SIZE - 11, Math.max(11, start.y)) };
        used.push(fallback);
        return fallback;
    }

    async function buildCard(character, index) {
        const card = document.createElement('section');
        card.className = 'stroke-card';
        card.setAttribute('aria-label', 'Stroke order for ' + character);
        const heading = document.createElement('h3');
        heading.className = 'character-label';
        heading.textContent = character;
        const stage = document.createElement('div');
        stage.className = 'character-stage';
        const target = document.createElement('div');
        target.className = 'character-target';
        target.id = 'hanzi-target-' + index;
        const overlay = svgElement('svg', { viewBox:'0 0 ' + SIZE + ' ' + SIZE, 'aria-hidden':'true' });
        overlay.classList.add('number-layer');
        stage.append(target, overlay);
        const label = document.createElement('label');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = true;
        checkbox.setAttribute('aria-label', 'Show stroke numbers for ' + character);
        label.append(checkbox, document.createTextNode('Show stroke numbers'));
        const status = document.createElement('p');
        status.className = 'status';
        status.textContent = 'Loading strokes…';
        const pause = document.createElement('button');
        pause.type = 'button';
        pause.disabled = true;
        pause.textContent = reducedMotion ? 'Play strokes' : 'Pause';
        pause.setAttribute('aria-label', 'Pause stroke animation for ' + character);
        card.append(heading, stage, label, status, pause);
        document.getElementById('stroke-cards').append(card);
        checkbox.addEventListener('change', () => { overlay.hidden = !checkbox.checked; });
        try {
            if (!window.HanziWriter) throw new Error('Stroke library did not load');
            const data = await HanziWriter.loadCharacterData(character);
            const transform = HanziWriter.getScalingTransform(SIZE, SIZE, PADDING);
            const coordinateGroup = svgElement('g', { transform:transform.transform });
            const matrix = coordinateGroup.transform.baseVal.consolidate().matrix;
            const positions = [];
            const medians = Array.isArray(data.medians) ? data.medians : [];
            medians.forEach((median, strokeIndex) => {
                if (!Array.isArray(median) || !median.length) return;
                const [x, y] = median[0];
                const start = { x:matrix.a * x + matrix.c * y + matrix.e, y:matrix.b * x + matrix.d * y + matrix.f };
                const badge = placeBadge(start, positions);
                const group = svgElement('g', { 'data-stroke-number':strokeIndex + 1 });
                group.classList.add('stroke-number');
                if (Math.hypot(badge.x - start.x, badge.y - start.y) > 4) {
                    const line = svgElement('line', { x1:start.x, y1:start.y, x2:badge.x, y2:badge.y });
                    line.classList.add('leader');
                    group.append(line);
                }
                group.append(svgElement('circle', { cx:badge.x, cy:badge.y, r:9 }));
                const number = svgElement('text', { x:badge.x, y:badge.y });
                number.textContent = String(strokeIndex + 1);
                group.append(number);
                overlay.append(group);
            });
            const writer = HanziWriter.create(target.id, character, {
                width:SIZE, height:SIZE, padding:PADDING,
                showOutline:true, showCharacter:reducedMotion,
                strokeColor:'#173f91', outlineColor:'#cbd5e1',
                strokeAnimationSpeed:1.5, delayBetweenStrokes:80,
                charDataLoader: (_char, success) => success(data)
            });
            let started = !reducedMotion;
            let paused = false;
            if (started) writer.loopCharacterAnimation();
            status.textContent = data.strokes.length + ' strokes' + (medians.length ? '' : ' — number labels unavailable');
            pause.disabled = false;
            pause.setAttribute('aria-label', (started ? 'Pause' : 'Play') + ' stroke animation for ' + character);
            pause.addEventListener('click', () => {
                if (!started) {
                    writer.loopCharacterAnimation();
                    started = true;
                    paused = false;
                } else if (paused) {
                    writer.resumeAnimation();
                    paused = false;
                } else {
                    writer.pauseAnimation();
                    paused = true;
                }
                pause.textContent = paused ? 'Resume' : 'Pause';
                pause.setAttribute('aria-label', (paused ? 'Resume' : 'Pause') + ' stroke animation for ' + character);
            });
            // Exposed on this local card for repeatable browser smoke tests.
            card.dataset.strokeCount = String(data.strokes.length);
            card.dataset.ready = 'true';
        } catch (error) {
            status.textContent = 'Strokes are unavailable. Please try this item again later.';
            status.classList.add('error');
            checkbox.disabled = true;
            card.dataset.ready = 'error';
        }
    }
    characters.forEach((character, index) => { buildCard(character, index); });
})();
</script>
</body>
</html>'''
    html_code = html_code.replace("__CHARACTERS__", json.dumps(chinese_chars, ensure_ascii=True))
    # Reserve room for a one-column phone layout; allow internal scrolling for long sentences.
    frame_height = min(len(chinese_chars) * 320 + 80, 720)
    components.html(html_code, height=frame_height, scrolling=True)

def rename_child_profile(old_name: str, new_name: str):
    if not new_name or new_name == old_name:
        return
    if old_name in st.session_state.children:
        idx = st.session_state.children.index(old_name)
        st.session_state.children[idx] = new_name
    
    st.session_state.active_child = new_name

    for key_prefix in ["active_week", "raw_words", "cached_analysis", "cached_analysis_version", "quiz_index", "quiz_score", "quiz_checked", "quiz_logged", "quiz_result", "mastered_words", "unfamiliar_words", "learn_item_index", "learn_item_context"]:
        old_key = f"{key_prefix}_{old_name}"
        new_key = f"{key_prefix}_{new_name}"
        if old_key in st.session_state:
            st.session_state[new_key] = st.session_state.pop(old_key)

    sync_child_profiles(st.session_state.children)


def prepare_item_navigation(state: Any, child_name: str, list_title: str, items: list[str]) -> tuple[str, int]:
    """Keep each learner's position in bounds; start at item 1 for a changed list."""
    index_key = f"learn_item_index_{child_name}"
    context_key = f"learn_item_context_{child_name}"
    context = (list_title, tuple(items))
    if state.get(context_key) != context:
        state[index_key] = 0
        state[context_key] = context
    try:
        position = int(state.get(index_key, 0))
    except (TypeError, ValueError):
        position = 0
    position = max(0, min(position, max(0, len(items) - 1)))
    state[index_key] = position
    return index_key, position


def move_learning_item(index_key: str, delta: int, item_count: int) -> None:
    """Streamlit calls this before rerendering, so one click moves exactly one item."""
    position = int(st.session_state.get(index_key, 0))
    st.session_state[index_key] = max(0, min(position + delta, max(0, item_count - 1)))


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

st.markdown(
    '<div class="hero">'
    '<h1>📖 Hi <span class="child-name">'
    + escape(str(active_child))
    + "!</span> Let's Learn Our Words!</h1></div>",
    unsafe_allow_html=True,
)

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

# One item at a time: this changes presentation, not analysis or spelling rules.
index_key, index = prepare_item_navigation(st.session_state, active_child, selected_week, words)
st.markdown(
    f'<div class="item-progress" role="status">Item {index + 1} of {len(words)}</div>',
    unsafe_allow_html=True,
)
with st.container(key="learn_item_navigation"):
    previous_col, next_col = st.columns(2, gap="small")
    with previous_col:
        st.button(
            "← Previous",
            key="learn_previous",
            disabled=index == 0,
            use_container_width=True,
            on_click=move_learning_item,
            args=(index_key, -1, len(words)),
            help="Show the previous item",
        )
    with next_col:
        st.button(
            "Next →",
            key="learn_next",
            disabled=index == len(words) - 1,
            use_container_width=True,
            on_click=move_learning_item,
            args=(index_key, 1, len(words)),
            help="Show the next item",
        )

word = words[index]
info = analysis.get(word, {})
lang = guess_language(word)  # Do not trust the model to classify Chinese targets.
with st.expander(f"Item {index + 1}:  {word} ({lang})", expanded=True):
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
            meaning_available = True
        elif is_valid_english_meaning(preset.get("meaning")):
            meaning = str(preset["meaning"]).strip()
            meaning_available = True
        else:
            meaning = ""
            meaning_available = False

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
        if meaning_available:
            st.write(f"💡 **Meaning:** {meaning}")
        if sentence:
            st.write(f"💬 **Example:** {sentence}")
        else:
            st.caption("A natural example sentence could not be generated. Ask a grown-up to refresh the word details.")
        if sentence:
            audio_button(sentence, "Chinese", f"sentence-{word}")
        if meaning_available:
            st.write(f"⭐ **Fun Memory Tip (记忆小贴士):** {tip}")
