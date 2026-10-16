from __future__ import annotations

import json
import requests
import streamlit as st

st.set_page_config(page_title="Magic Spelling World ✏️", page_icon="⭐", layout="centered")

API_URL = st.secrets.get("GSHEETS_API_URL", "").strip()

DEFAULT_LISTS = {
    "Week 1: School & Friends": "学校\n认真\n爸爸\n妈妈\napple\nschool\nfriend",
    "Week 2: Nature & Family": "mountain\nflower\n事情\n学习"
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600;700&display=swap');

html, body, [class*="css"], button, input, select {
    font-family: 'Fredoka', cursive, sans-serif !important;
    font-size: 1.15rem;
}

h1 { font-size: 2.8rem !important; color: #0284c7 !important; }
h2 { font-size: 2.2rem !important; color: #0369a1 !important; }
h3 { font-size: 1.7rem !important; color: #0f766e !important; }

.stButton > button {
    font-size: 1.3rem !important;
    font-weight: 700 !important;
    border-radius: 18px !important;
    padding: 0.6rem 1.2rem !important;
}

.hero {
    padding: 2.2rem 1.8rem; 
    border-radius: 28px; 
    background: linear-gradient(135deg, #fef9c3 0%, #e0f2fe 100%); 
    border: 4px solid #fde047;
    text-align: center;
    margin-bottom: 2rem;
    box-shadow: 0 8px 16px rgba(0,0,0,0.06);
}
.hero h1 { color: #0284c7; margin-bottom: 0.6rem; font-size: 2.8rem; }
.hero p { color: #334155; font-size: 1.35rem; margin: 0; }

.action-card {
    padding: 1.6rem;
    border-radius: 24px;
    border: 3px solid #bae6fd;
    text-align: center;
    background: #ffffff;
    box-shadow: 0 6px 12px rgba(0,0,0,0.05);
}
.action-card h3 { font-size: 1.8rem; color: #0284c7; margin-bottom: 0.4rem; }
.action-card p { font-size: 1.15rem; color: #475569; }
</style>
""", unsafe_allow_html=True)


def fetch_remote_lists(child_name: str = "") -> dict[str, str]:
    if API_URL:
        try:
            params = {"action": "get_lists"}
            if child_name:
                params["child_name"] = child_name
            resp = requests.get(API_URL, params=params, allow_redirects=True, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and data:
                    return data
        except Exception:
            pass
    return DEFAULT_LISTS


def save_remote_list(title: str, words: str, child_name: str) -> None:
    if API_URL:
        try:
            requests.post(API_URL, json={"action": "save", "title": title, "words": words, "child_name": child_name}, timeout=5)
        except Exception as e:
            st.error(f"Failed to sync save to database: {e}")


def delete_remote_list(title: str, child_name: str) -> None:
    if API_URL:
        try:
            requests.post(API_URL, json={"action": "delete", "title": title, "child_name": child_name}, timeout=5)
        except Exception as e:
            st.error(f"Failed to sync delete to database: {e}")


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
        except Exception as e:
            st.error(f"Failed to sync learner profiles: {e}")


if "children" not in st.session_state:
    st.session_state.children = fetch_child_profiles()

if "active_child" not in st.session_state:
    st.session_state.active_child = st.session_state.children[0]

active_child = st.session_state.active_child

fetched = fetch_remote_lists(active_child)
if f"archived_lists_{active_child}" not in st.session_state or not st.session_state[f"archived_lists_{active_child}"]:
    st.session_state[f"archived_lists_{active_child}"] = fetched

if "parent_unlocked" not in st.session_state:
    st.session_state.parent_unlocked = False


def rename_child_profile(old_name: str, new_name: str):
    if not new_name or new_name == old_name:
        return
    if old_name in st.session_state.children:
        idx = st.session_state.children.index(old_name)
        st.session_state.children[idx] = new_name
    
    st.session_state.active_child = new_name

    for key_prefix in ["active_week", "raw_words", "cached_analysis", "quiz_index", "quiz_score", "quiz_checked", "quiz_logged", "quiz_result", "mastered_words", "unfamiliar_words", "archived_lists"]:
        old_key = f"{key_prefix}_{old_name}"
        new_key = f"{key_prefix}_{new_name}"
        if old_key in st.session_state:
            st.session_state[new_key] = st.session_state.pop(old_key)

    sync_child_profiles(st.session_state.children)


with st.sidebar:
    st.subheader("👤 Who is practicing today?")
    
    selected_child = st.selectbox(
        "Select Learner:",
        options=st.session_state.children,
        index=st.session_state.children.index(st.session_state.active_child) if st.session_state.active_child in st.session_state.children else 0
    )
    if selected_child != st.session_state.active_child:
        st.session_state.active_child = selected_child
        st.rerun()

    active_child = st.session_state.active_child

    with st.expander("✏️ Edit Current Learner Name", expanded=False):
        edited_name = st.text_input("New Name:", value=active_child, key=f"rename_input_{active_child}")
        if st.button("Save New Name", type="primary", use_container_width=True):
            clean_rename = edited_name.strip()
            if clean_rename and clean_rename != active_child:
                rename_child_profile(active_child, clean_rename)
                st.success(f"Renamed to {clean_rename}!")
                st.rerun()

    with st.expander("➕ Add New Learner", expanded=False):
        new_child_name = st.text_input("Child's Name:", placeholder="e.g., Lucas", key="add_new_child_input")
        if st.button("Add Learner Profile", type="secondary", use_container_width=True):
            clean_name = new_child_name.strip()
            if clean_name and clean_name not in st.session_state.children:
                st.session_state.children.append(clean_name)
                st.session_state.active_child = clean_name
                sync_child_profiles(st.session_state.children)
                st.success(f"Added profile for {clean_name}!")
                st.rerun()

active_child = st.session_state.active_child

st.markdown(f"""
<div class="hero">
    <h1>👋 Hi {active_child}! Welcome to Magic Spelling World! ✏️</h1>
    <p>Listen, practice handwriting, and master Chinese & English spelling today!</p>
</div>
""", unsafe_allow_html=True)

st.write(f"### 🚀 What would **{active_child}** like to do?")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="action-card">
        <h3>📖 Learn Words</h3>
        <p>Explore meanings, pinyin, stroke orders & memory tricks!</p>
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    if st.button(f"👉 Learn Words for {active_child}", type="primary", use_container_width=True):
        st.switch_page("pages/1_📖_Learn_Words.py")

with col2:
    st.markdown("""
    <div class="action-card">
        <h3>🎯 Dictation Quiz</h3>
        <p>Listen to audio & test your handwriting!</p>
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    if st.button(f"👉 Start Dictation Quiz", type="primary", use_container_width=True):
        st.switch_page("pages/2_🎯_Dictation_Quiz.py")

st.divider()

PARENT_PIN = "6666"

with st.expander("🔒 Parent Area: Manage Spelling Lists (PIN Required)", expanded=False):
    st.caption("Grown-ups only! Enter PIN to add, update, or delete spelling lists.")

    if not st.session_state.parent_unlocked:
        entered_pin = st.text_input("Enter 4-digit Parent PIN:", type="password", key="pin_entry_field")
        if entered_pin == PARENT_PIN:
            st.session_state.parent_unlocked = True
            st.rerun()
        elif entered_pin != "":
            st.error("❌ Incorrect PIN. Please try again.")
    else:
        st.success("🔓 Unlocked!")
        if st.button("🔒 Lock Parent Area Now", type="secondary"):
            st.session_state.parent_unlocked = False
            st.rerun()

        st.write("---")
        
        st.write("### ➕ Add or Update List")
        target_child_for_list = st.selectbox(
            "Assign List To:",
            options=["All Learners"] + st.session_state.children,
            index=1 if active_child in st.session_state.children else 0,
            key="target_child_list_select"
        )
        new_week_title = st.text_input("Week Title / Name:", placeholder="e.g., Week 5: Animals & Weather")
        new_week_words = st.text_area("Spelling Words (one word per line):", height=120, placeholder="elephant\nrainbow\n事情\n生日")
        
        if st.button("💾 Save List to Google Sheets", type="primary"):
            title_clean = new_week_title.strip()
            words_clean = new_week_words.strip()
            if title_clean and words_clean:
                save_remote_list(title_clean, words_clean, target_child_for_list)
                st.session_state.parent_unlocked = False
                st.success(f"Saved '{title_clean}' for {target_child_for_list} successfully!")
                st.rerun()
            else:
                st.warning("Please enter both a title and words before saving.")

        st.divider()

        st.write("### 🗑️ Delete an Existing List")
        child_lists = fetch_remote_lists(active_child)
        if child_lists:
            list_to_delete = st.selectbox(
                f"Select list to delete for {active_child}:",
                options=list(child_lists.keys()),
                key="delete_list_select"
            )
            if st.button(f"❌ Delete '{list_to_delete}'", type="secondary"):
                delete_remote_list(list_to_delete, active_child)
                st.session_state.parent_unlocked = False
                st.success(f"Deleted '{list_to_delete}'!")
                st.rerun()
        else:
            st.caption("No archived lists to delete for this child.")
