from __future__ import annotations

import datetime
import io
import json
import hashlib
import re
import requests
import streamlit as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from shared_theme import apply_shared_theme
from audio_prefetch import AudioPrefetcher
import streamlit.components.v1 as components
from gtts import gTTS

st.set_page_config(
    page_title="Dictation Quiz 🎯",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Fixed sidebar labels/order; keep deployed filenames and app.py unchanged.
st.sidebar.page_link('app.py', label='Home')
st.sidebar.page_link('pages/1_📖_Learn_Words.py', label='Learn Words', icon='📖')
st.sidebar.page_link('pages/2_🎯_Dictation_Quiz.py', label='Dictation Quiz', icon='🎯')
st.sidebar.page_link('pages/5_More_Practices.py', label='Bookmarks', icon='🔖')
st.sidebar.page_link('pages/4_🌱_Word Garden.py', label='Word Garden', icon='🌱')
st.sidebar.page_link('pages/3_📊_Parent_Summary.py', label='Parent Summary', icon='📊')
st.sidebar.divider()

API_URL = st.secrets.get("GSHEETS_API_URL", "").strip()

apply_shared_theme()

# Page-specific visual accents only; behavior and data flow remain unchanged.
st.markdown("""
<style>
/* Dictation keeps a focused blue/purple lesson surface within the shared theme. */
[data-testid="stProgress"] { margin:.7rem 0 1rem; }
[data-testid="stAlert"] { border:2px solid #c6d7f2; }
[data-testid="stAudio"] { border-radius:16px; }
[data-testid="stTextInput"] input:disabled { color:#1f2937 !important; background:#f1f5f9 !important; }
[data-testid="stHorizontalBlock"] [data-testid="stColumn"] { min-width:0; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=15, show_spinner=False)
def fetch_available_lists(child_name: str = "") -> dict[str, str]:
    if API_URL:
        try:
            params = {"action": "get_lists"}
            if child_name:
                params["child_name"] = child_name
            resp = requests.get(API_URL, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and data:
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


def log_completed_quiz(child_name: str, week_title: str, score: int, total_words: int, mastered: set, unfamiliar: set):
    if API_URL:
        try:
            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
            payload = {
                "action": "log_quiz",
                "timestamp": now_str,
                "child_name": child_name,
                "week_title": week_title,
                "score": score,
                "total_words": total_words,
                "mastered": ", ".join(mastered) if mastered else "None",
                "unfamiliar": ", ".join(unfamiliar) if unfamiliar else "None"
            }
            requests.post(API_URL, json=payload, timeout=5)
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Failed to log quiz attempt: {e}")


@st.cache_data(show_spinner=False, max_entries=256, ttl=3600)
def generate_speech_audio(text: str, lang: str) -> bytes:
    fp = io.BytesIO()
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.write_to_fp(fp)
    return fp.getvalue()


@st.cache_resource(show_spinner=False)
def get_audio_prefetcher() -> AudioPrefetcher:
    return AudioPrefetcher(generate_speech_audio, max_workers=2)


def speech_language(text: str) -> str:
    return "zh-cn" if re.search(r'[\u4e00-\u9fff]', text) else "en"


def prefetch_speech_audio(text: str) -> None:
    get_audio_prefetcher().prefetch(text, speech_language(text))


def speak_text(text: str):
    try:
        lang = speech_language(text)
        audio_bytes = get_audio_prefetcher().prefetch(text, lang).result()
        st.audio(audio_bytes, format="audio/mp3", autoplay=True)
    except Exception:
        st.warning("Audio playback failed.")


def render_character_writing_pads(count: int, instance_key: str) -> None:
    """Render separate, fast native-canvas boxes inside a single iframe."""
    if count <= 0:
        return

    pad_markup = "".join(
        f'<section class="pad"><strong>Character {idx + 1} of {count}</strong>'
        f'<canvas class="writepad" width="170" height="170" '
        f'aria-label="Writing pad for character {idx + 1} of {count}" tabindex="0"></canvas>'
        f'<button type="button" class="clear" data-pad="{idx}" '
        f'aria-label="Clear character {idx + 1}">Clear this box</button></section>'
        for idx in range(count)
    )
    html_code = '''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}body{margin:0;padding:4px;font-family:Arial,sans-serif;color:#1f2937}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.pad{min-width:0;border:2px solid #94a3b8;border-radius:12px;padding:8px;background:#fff}
.pad strong{display:block;margin:0 0 6px;font-size:15px;line-height:20px}
.writepad{display:block;width:min(100%,170px);height:auto;aspect-ratio:1;background:#fff;
border:2px solid #0f766e;border-radius:8px;touch-action:none;cursor:crosshair}
.clear{margin-top:6px;min-height:36px;border:1px solid #1d4ed8;border-radius:8px;
background:#eff6ff;color:#1e3a8a;font-size:14px;font-weight:700;padding:4px 10px;cursor:pointer}
.clear:focus-visible,.writepad:focus-visible{outline:3px solid #f59e0b;outline-offset:2px}
</style></head><body><div class="grid" data-question-key="__QUESTION_KEY__">__PAD_MARKUP__</div>
<script>
for(const canvas of document.querySelectorAll('.writepad')){
 const ctx=canvas.getContext('2d');ctx.lineWidth=7;ctx.lineCap='round';ctx.lineJoin='round';ctx.strokeStyle='#111827';
 let drawing=false;
 const point=e=>{const r=canvas.getBoundingClientRect();return{x:(e.clientX-r.left)*canvas.width/r.width,y:(e.clientY-r.top)*canvas.height/r.height}};
 canvas.addEventListener('pointerdown',e=>{if(e.pointerType==='mouse'&&e.button!==0)return;e.preventDefault();drawing=true;canvas.setPointerCapture(e.pointerId);const p=point(e);ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(p.x+0.1,p.y+0.1);ctx.stroke()});
 canvas.addEventListener('pointermove',e=>{if(!drawing)return;e.preventDefault();const p=point(e);ctx.lineTo(p.x,p.y);ctx.stroke()});
 const finish=e=>{if(!drawing)return;drawing=false;ctx.closePath();if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId)};
 canvas.addEventListener('pointerup',finish);canvas.addEventListener('pointercancel',finish);
}
document.querySelectorAll('.clear').forEach(button=>button.addEventListener('click',()=>{
 const canvas=button.closest('.pad').querySelector('.writepad');canvas.getContext('2d').clearRect(0,0,canvas.width,canvas.height)
}));
</script></body></html>'''
    html_code = html_code.replace("__QUESTION_KEY__", instance_key).replace("__PAD_MARKUP__", pad_markup)
    rows = (count + 1) // 2
    components.html(html_code, height=rows * 280 + 20, scrolling=False)


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

    num_rows = (len(chinese_chars) + 2) // 3
    html_code = f"""<!DOCTYPE html><html><head><script src="https://cdn.jsdelivr.net/npm/hanzi-writer@3.5/dist/hanzi-writer.min.js"></script></head><body style="margin:0;padding:0;background:transparent;"><div style="display:flex;flex-wrap:wrap;gap:10px;justify-content:center;align-items:center;">{targets}</div><script>{scripts}</script></body></html>"""
    components.html(html_code, height=num_rows * 125 + 15)


def normalize_words(raw: str) -> list[str]:
    seen: set[str] = set()
    result = []
    for line in raw.replace("，", "\n").replace(",", "\n").splitlines():
        item = line.strip()
        if item and item.casefold() not in seen:
            seen.add(item.casefold())
            result.append(item)
    return result


def reset_quiz_state(child_name: str):
    st.session_state[f"quiz_index_{child_name}"] = 0
    st.session_state[f"quiz_score_{child_name}"] = 0
    st.session_state[f"quiz_checked_{child_name}"] = False
    st.session_state[f"quiz_logged_{child_name}"] = False
    st.session_state[f"quiz_result_{child_name}"] = None
    st.session_state[f"mastered_words_{child_name}"] = set()
    st.session_state[f"unfamiliar_words_{child_name}"] = set()


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
        edited_name = st.text_input("New Name:", value=active_child, key=f"p2_rename_input_{active_child}")
        if st.button("Save New Name", type="primary", use_container_width=True):
            clean_rename = edited_name.strip()
            if clean_rename and clean_rename != active_child:
                rename_child_profile(active_child, clean_rename)
                st.success(f"Renamed to {clean_rename}!")
                st.rerun()

active_child = st.session_state.active_child

st.title(f"🎯 Hi {active_child}! Dictation Quiz Time!")

available_lists = fetch_available_lists(active_child)
list_titles = list(available_lists.keys())

if not list_titles:
    st.info(f"📋 No dictation lists assigned to {active_child} yet. Grown-ups can add lists on the home page!")
    st.stop()

current_active = st.session_state.get(f"active_week_{active_child}", "")
if current_active not in list_titles and list_titles:
    st.session_state[f"active_week_{active_child}"] = list_titles[0]
    st.session_state[f"raw_words_{active_child}"] = available_lists[list_titles[0]]
    reset_quiz_state(active_child)

default_idx = list_titles.index(st.session_state[f"active_week_{active_child}"]) if st.session_state[f"active_week_{active_child}"] in list_titles else 0

selected_list_title = st.selectbox(
    f"📋 Select Dictation List for {active_child}:",
    options=list_titles,
    index=default_idx
)

if selected_list_title != st.session_state.get(f"active_week_{active_child}"):
    st.session_state[f"active_week_{active_child}"] = selected_list_title
    st.session_state[f"raw_words_{active_child}"] = available_lists[selected_list_title]
    reset_quiz_state(active_child)
    st.rerun()

quiz_words = normalize_words(st.session_state.get(f"raw_words_{active_child}", ""))

if not quiz_words:
    st.warning("⚠️ No words found in the selected list. Please choose a different list above!")
    st.stop()

if f"quiz_index_{active_child}" not in st.session_state:
    st.session_state[f"quiz_index_{active_child}"] = 0
if f"quiz_score_{active_child}" not in st.session_state:
    st.session_state[f"quiz_score_{active_child}"] = 0
if f"quiz_checked_{active_child}" not in st.session_state:
    st.session_state[f"quiz_checked_{active_child}"] = False
if f"quiz_logged_{active_child}" not in st.session_state:
    st.session_state[f"quiz_logged_{active_child}"] = False
if f"quiz_result_{active_child}" not in st.session_state:
    st.session_state[f"quiz_result_{active_child}"] = None
if f"mastered_words_{active_child}" not in st.session_state:
    st.session_state[f"mastered_words_{active_child}"] = set()
if f"unfamiliar_words_{active_child}" not in st.session_state:
    st.session_state[f"unfamiliar_words_{active_child}"] = set()

total_q = len(quiz_words)
current_idx = st.session_state[f"quiz_index_{active_child}"]
pad_fingerprint = hashlib.sha256(
    (active_child + "\0" + selected_list_title + "\0" + "\0".join(quiz_words)).encode("utf-8")
).hexdigest()[:12]

if current_idx >= total_q:
    st.balloons()
    st.success(f"🎉 Quiz Completed! Outstanding effort, {active_child}!")
    
    final_score = st.session_state[f"quiz_score_{active_child}"]
    st.metric(label="Final Score", value=f"{final_score} / {total_q}")

    if not st.session_state[f"quiz_logged_{active_child}"]:
        log_completed_quiz(
            child_name=active_child,
            week_title=selected_list_title,
            score=final_score,
            total_words=total_q,
            mastered=st.session_state[f"mastered_words_{active_child}"],
            unfamiliar=st.session_state[f"unfamiliar_words_{active_child}"]
        )
        st.session_state[f"quiz_logged_{active_child}"] = True
        st.info(f"✅ {active_child}'s score and practice details have been saved to Parent History!")

    if st.button("🌱 See My Word Garden", type="primary"):
        st.switch_page("pages/4_🌱_Word Garden.py")

    if st.button("🔄 Restart Quiz", type="primary"):
        reset_quiz_state(active_child)
        st.rerun()
    st.stop()

target_word = quiz_words[current_idx]
is_chinese = bool(re.search(r'[\u4e00-\u9fff]', target_word))
for upcoming_word in quiz_words[current_idx:current_idx + 2]:
    prefetch_speech_audio(upcoming_word)

st.progress((current_idx) / total_q)
st.caption(f"Question {current_idx + 1} of {total_q} — **{selected_list_title}**")

st.write("### 🔊 Listen to the Word:")
audio_col1, audio_col2 = st.columns([1, 2])
with audio_col1:
    if st.button("🔊 Play Sound", type="primary", use_container_width=True):
        speak_text(target_word)

st.write("---")

if is_chinese:
    character_pads = re.findall(r'[\u4e00-\u9fff]', target_word)
    pad_col, answer_col = st.columns([1, 1], gap="medium")

    with pad_col:
        st.markdown(f"### ✏️ Chinese Writing Pads — {len(character_pads)} boxes")
        st.caption("Write one character in each box. Check your answer to reveal the word and stroke guide.")
        render_character_writing_pads(
            len(character_pads),
            f"{pad_fingerprint}_{current_idx}",
        )

    with answer_col:
        if st.session_state[f"quiz_checked_{active_child}"]:
            st.markdown(f"### 🔍 Correct Word: **{target_word}**")
            render_hanzi_animations(target_word)
        else:
            st.markdown("### 🔎 Check your writing")
            st.caption("The correct word and stroke guide will appear here after you check.")

    st.write("---")

    if not st.session_state[f"quiz_checked_{active_child}"]:
        btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
        with btn_col2:
            if st.button("🔍 Check Answer & Stroke Order", type="primary", use_container_width=True):
                st.session_state[f"quiz_checked_{active_child}"] = True
                st.rerun()
    else:
        if st.session_state[f"quiz_result_{active_child}"] is None:
            st.markdown("<h3 style='text-align: center;'>📝 How did your writing look?</h3>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            
            with c1:
                if st.button("🌟 Pass / Correct", type="primary", use_container_width=True):
                    st.session_state[f"quiz_score_{active_child}"] += 1
                    st.session_state[f"mastered_words_{active_child}"].add(target_word)
                    st.session_state[f"quiz_result_{active_child}"] = "correct"
                    st.rerun()

            with c2:
                if st.button("❌ Needs Practice", type="secondary", use_container_width=True):
                    st.session_state[f"unfamiliar_words_{active_child}"].add(target_word)
                    st.session_state[f"quiz_result_{active_child}"] = "incorrect"
                    st.rerun()

        else:
            if st.session_state[f"quiz_result_{active_child}"] == "correct":
                st.success(f"🌟 Marked Correct! Great job, {active_child}!")
            else:
                st.warning(f"💡 Marked for practice! Keep it up, {active_child}!")

            btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
            with btn_col2:
                if st.button("➡️ Next Word", type="primary", use_container_width=True):
                    st.session_state[f"quiz_index_{active_child}"] += 1
                    st.session_state[f"quiz_checked_{active_child}"] = False
                    st.session_state[f"quiz_result_{active_child}"] = None
                    st.rerun()

else:
    st.markdown("### 🔤 Type Your English Spelling Answer:")
    
    typed_ans = st.text_input(
        "Type word here:",
        placeholder="Type the word you heard...",
        key=f"eng_input_{active_child}_{selected_list_title}_{current_idx}",
        disabled=st.session_state[f"quiz_checked_{active_child}"]
    )

    st.write("")

    if not st.session_state[f"quiz_checked_{active_child}"]:
        btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
        with btn_col2:
            if st.button("✅ Check English Spelling", type="primary", use_container_width=True):
                clean_user = typed_ans.strip().casefold()
                clean_target = target_word.strip().casefold()
                
                if clean_user == clean_target:
                    st.session_state[f"quiz_score_{active_child}"] += 1
                    st.session_state[f"mastered_words_{active_child}"].add(target_word)
                    st.session_state[f"quiz_result_{active_child}"] = "correct"
                else:
                    st.session_state[f"unfamiliar_words_{active_child}"].add(target_word)
                    st.session_state[f"quiz_result_{active_child}"] = "incorrect"

                st.session_state[f"quiz_checked_{active_child}"] = True
                st.rerun()

    else:
        if st.session_state[f"quiz_result_{active_child}"] == "correct":
            st.success(f"🌟 Correct Spelling! Awesome job, {active_child}: **{target_word}**")
        else:
            st.error(f"❌ Correct Spelling: **{target_word}**")

        st.write("")
        btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
        with btn_col2:
            if st.button("➡️ Next Word", type="primary", use_container_width=True):
                st.session_state[f"quiz_index_{active_child}"] += 1
                st.session_state[f"quiz_checked_{active_child}"] = False
                st.session_state[f"quiz_result_{active_child}"] = None
                st.rerun()
