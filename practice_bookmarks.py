"""Persistent Bookmarks bookmarks. No API keys or session-only fallback storage."""
from __future__ import annotations

import hashlib
import json
from html import escape
from typing import Any

import requests
import streamlit as st

FEATURE = "more_practices"
VERSION = 1
NOT_READY = "Bookmarks is not ready yet. A grown-up needs to update the Apps Script deployment using the supplied Code.gs."


def _request(api_url: str, method: str, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    if not api_url:
        return None, "Google Sheets is not configured. Bookmarks cannot be saved yet."
    try:
        if method == "GET":
            response = requests.get(api_url, params=payload, allow_redirects=True, timeout=10)
        else:
            response = requests.post(api_url, json=payload, allow_redirects=True, timeout=10)
        if response.status_code != 200:
            return None, "Could not reach saved practices. Please try again."
        result = response.json()
    except (requests.RequestException, ValueError, TypeError):
        return None, "Could not reach saved practices. Please try again."
    if not isinstance(result, dict) or result.get("feature") != FEATURE or result.get("version") != VERSION:
        # The original backend returns {status:success} even for unknown POST actions.
        return None, NOT_READY
    if result.get("status") != "success":
        message = result.get("message")
        return None, str(message) if isinstance(message, str) and message else "The bookmark change could not be confirmed. Please try again."
    return result, None


@st.cache_data(ttl=15, max_entries=256, show_spinner=False)
def fetch_bookmarks(api_url: str, child_name: str) -> tuple[list[dict[str, str]], str | None]:
    result, error = _request(api_url, "GET", {"action": "get_bookmarks", "child_name": child_name})
    if error:
        return [], error
    records = result.get("bookmarks") if result else None
    if not isinstance(records, list):
        return [], "Saved practices returned an unexpected response. Please try again."
    valid: list[dict[str, str]] = []
    for record in records:
        if not isinstance(record, dict) or not all(isinstance(record.get(key), str) and record[key] for key in ("id", "child_name", "list_title", "word")):
            return [], "Saved practices returned an unexpected response. Please try again."
        if record["child_name"].strip().casefold() != child_name.strip().casefold():
            return [], "The saved-practice response did not match this learner. Please refresh."
        valid.append({key: str(record.get(key, "")) for key in ("id", "child_name", "list_title", "word", "created_at")})
    return valid, None


def change_bookmark(api_url: str, action: str, **fields: str) -> str | None:
    result, error = _request(api_url, "POST", {"action": action, **fields})
    fetch_bookmarks.clear()
    if not error and action == "add_bookmark":
        bookmark = result.get("bookmark") if result else None
        if not isinstance(bookmark, dict) or not isinstance(bookmark.get("id"), str) or not bookmark["id"] or any(bookmark.get(key) != fields.get(key) for key in ("list_title", "word")) or str(bookmark.get("child_name", "")).strip().casefold() != fields.get("child_name", "").strip().casefold():
            return "The bookmark save could not be confirmed. Refresh to check it before trying again."
    if not error and action == "clear_bookmark" and not isinstance(result.get("removed"), bool):
        return "The bookmark clear could not be confirmed. Refresh to check it before trying again."
    if not error and action == "rename_bookmarks" and (not isinstance(result.get("renamed"), int) or isinstance(result.get("renamed"), bool)):
        return "Moving saved practices could not be confirmed. Please refresh before renaming again."
    return error


def bookmark_widget_key(child_name: str, list_title: str, word: str) -> str:
    identity = json.dumps([child_name.casefold(), list_title, word], ensure_ascii=False)
    return "save_practice_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def _flash(child_name: str, message: str, error: bool = False) -> None:
    st.session_state[f"practice_flash_{child_name}"] = {"message": message, "error": error}


def show_bookmark_feedback(child_name: str) -> None:
    feedback = st.session_state.pop(f"practice_flash_{child_name}", None)
    if feedback:
        (st.error if feedback["error"] else st.success)(feedback["message"])


def on_bookmark_toggle(api_url: str, child_name: str, list_title: str, word: str, widget_key: str, bookmark_id: str) -> None:
    if st.session_state.get(widget_key, False):
        error = change_bookmark(api_url, "add_bookmark", child_name=child_name, list_title=list_title, word=word)
        _flash(child_name, error or "Saved to Bookmarks", bool(error))
    else:
        error = change_bookmark(api_url, "clear_bookmark", child_name=child_name, id=bookmark_id)
        _flash(child_name, error or "Cleared from Bookmarks. The original list is unchanged.", bool(error))


def clear_saved_practice(api_url: str, child_name: str, bookmark_id: str) -> None:
    error = change_bookmark(api_url, "clear_bookmark", child_name=child_name, id=bookmark_id)
    _flash(child_name, error or "Cleared! You can bookmark this item again whenever you like.", bool(error))


def rename_saved_practices(api_url: str, old_name: str, new_name: str) -> str | None:
    if not api_url:
        return None  # Existing offline learner renaming remains available.
    return change_bookmark(api_url, "rename_bookmarks", old_name=old_name, new_name=new_name)


def render_bookmark_checkbox(api_url: str, child_name: str, list_title: str, word: str, records: list[dict[str, str]], error: str | None) -> None:
    existing = next((record for record in records if record["list_title"] == list_title and record["word"] == word), None)
    key = bookmark_widget_key(child_name, list_title, word)
    st.session_state[key] = existing is not None
    st.checkbox(
        "Bookmark this item",
        key=key,
        disabled=bool(error),
        on_change=on_bookmark_toggle,
        args=(api_url, child_name, list_title, word, key, existing["id"] if existing else ""),
        help="Save this whole word, phrase, or sentence for another practice session. Uncheck or use Clear to remove only its bookmark.",
    )
    if error:
        st.caption(error)


@st.cache_data(ttl=15, show_spinner=False)
def fetch_profiles(api_url: str) -> list[str]:
    try:
        if api_url:
            response = requests.get(api_url, params={"action": "get_profiles"}, timeout=5)
            data = response.json()
            if response.status_code == 200 and isinstance(data, list) and all(isinstance(name, str) for name in data) and data:
                return data
    except (requests.RequestException, ValueError, TypeError):
        pass
    return ["Alex", "Emma"]


@st.cache_data(ttl=15, show_spinner=False)
def fetch_lists(api_url: str, child_name: str) -> tuple[dict[str, str], str | None]:
    try:
        if api_url:
            response = requests.get(api_url, params={"action": "get_lists", "child_name": child_name}, timeout=5)
            data = response.json()
            if response.status_code == 200 and isinstance(data, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in data.items()):
                return data, None
    except (requests.RequestException, ValueError, TypeError):
        pass
    return {}, "Cannot load spelling lists right now. Your saved bookmarks have not been removed."


def parse_list_items(raw_words: str) -> list[str]:
    return [line.strip() for line in raw_words.replace("，", "\n").replace(",", "\n").splitlines() if line.strip()]


def open_saved_practice(child_name: str, record: dict[str, str], available_lists: dict[str, str]) -> None:
    title = record["list_title"]
    items = parse_list_items(available_lists.get(title, ""))
    if record["word"] not in items:
        st.warning("This saved item is no longer in the current spelling list. Its bookmark is still here; Clear removes only the bookmark.")
        return
    raw = available_lists[title]
    if st.session_state.get(f"active_week_{child_name}") != title or st.session_state.get(f"raw_words_{child_name}") != raw:
        st.session_state[f"cached_analysis_{child_name}"] = {}
        st.session_state[f"cached_analysis_version_{child_name}"] = 0
    st.session_state.active_child = child_name
    st.session_state[f"active_week_{child_name}"] = title
    st.session_state[f"raw_words_{child_name}"] = raw
    st.session_state[f"learn_item_context_{child_name}"] = (title, tuple(items))
    st.session_state[f"learn_item_index_{child_name}"] = items.index(record["word"])
    st.switch_page("pages/1_📖_Learn_Words.py")


def apply_practice_theme() -> None:
    st.markdown(PRACTICE_THEME_CSS, unsafe_allow_html=True)


PRACTICE_THEME_CSS = r"""
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
[data-testid="stCheckbox"] label { min-height:48px; align-items:center; }
[data-testid="stCheckbox"] label p { font-weight:700 !important; }

/* Sidebar text rules must not override high-contrast button labels. */
[data-testid="stSidebar"] [data-testid="stButton"] button p,
[data-testid="stSidebar"] [data-testid="stButton"] button span { color:#ffffff !important; }
[data-testid="stSidebar"] [data-testid="stButton"] button:disabled p,
[data-testid="stSidebar"] [data-testid="stButton"] button:disabled span { color:#374151 !important; }

/* Child-friendly native sidebar controls. Keep Streamlit's own click/keyboard behavior. */
button[data-testid="stExpandSidebarButton"],
button[aria-label="Expand sidebar"],
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="collapsedControl"] button,
button[data-testid="stSidebarCollapsedControl"],
button[data-testid="collapsedControl"] {
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    gap:10px !important;
    width:auto !important;
    min-width:156px !important;
    min-height:56px !important;
    padding:10px 16px !important;
    background:#173f91 !important;
    color:#ffffff !important;
    border:3px solid #ffc94a !important;
    border-radius:16px !important;
    box-shadow:0 3px 0 #12336f,0 5px 14px rgba(17,24,39,.20) !important;
    opacity:1 !important;
    visibility:visible !important;
    cursor:pointer !important;
    transition:background-color .15s ease,box-shadow .15s ease !important;
}
button[data-testid="stExpandSidebarButton"]::after,
button[aria-label="Expand sidebar"]::after,
[data-testid="stSidebarCollapsedControl"] button::after,
[data-testid="collapsedControl"] button::after,
button[data-testid="stSidebarCollapsedControl"]::after,
button[data-testid="collapsedControl"]::after {
    content:"Open menu" !important;
    color:#ffffff !important;
    font:800 17px/1.2 'Nunito','Trebuchet MS',Arial,sans-serif !important;
    white-space:nowrap !important;
}
button[data-testid="stExpandSidebarButton"] span,
button[aria-label="Expand sidebar"] span,
[data-testid="stSidebarCollapsedControl"] button span,
[data-testid="collapsedControl"] button span {
    color:#ffffff !important;
    font-size:28px !important;
    opacity:1 !important;
}
button[data-testid="stExpandSidebarButton"] svg,
button[aria-label="Expand sidebar"] svg,
[data-testid="stSidebarCollapsedControl"] button svg,
[data-testid="collapsedControl"] button svg {
    width:28px !important;
    height:28px !important;
    color:#ffffff !important;
    opacity:1 !important;
}
button[data-testid="stExpandSidebarButton"]:hover,
button[aria-label="Expand sidebar"]:hover {
    background:#12336f !important;
    box-shadow:0 3px 0 #0c2451,0 6px 18px rgba(17,24,39,.24) !important;
}
button[data-testid="stExpandSidebarButton"]:focus-visible,
button[aria-label="Expand sidebar"]:focus-visible {
    outline:3px solid #111827 !important;
    outline-offset:3px !important;
}
[data-testid="stHeader"]:has(button[aria-label="Expand sidebar"]) {
    min-height:72px !important;
    overflow:visible !important;
}
/* Leave room below the visible menu control instead of covering page content. */
[data-testid="stAppViewContainer"]:has(button[aria-label="Expand sidebar"]) [data-testid="stMainBlockContainer"] {
    padding-top:5.25rem !important;
}
button[aria-label="Collapse sidebar"],
[data-testid="stSidebarCollapseButton"] button {
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    gap:6px !important;
    min-width:106px !important;
    min-height:48px !important;
    padding:8px 12px !important;
    background:#ffc94a !important;
    color:#111827 !important;
    border:2px solid #6b4e00 !important;
    border-radius:14px !important;
    opacity:1 !important;
    cursor:pointer !important;
}
button[aria-label="Collapse sidebar"]::after,
[data-testid="stSidebarCollapseButton"] button::after {
    content:"Close" !important;
    color:#111827 !important;
    font:800 16px/1.2 'Nunito','Trebuchet MS',Arial,sans-serif !important;
}
button[aria-label="Collapse sidebar"] span,
[data-testid="stSidebarCollapseButton"] button span {
    color:#111827 !important;
    font-size:26px !important;
    opacity:1 !important;
}
button[aria-label="Collapse sidebar"]:focus-visible {
    outline:3px solid #173f91 !important;
    outline-offset:3px !important;
}
@media (prefers-reduced-motion:reduce) {
    button[aria-label="Expand sidebar"],
    button[aria-label="Collapse sidebar"] { transition:none !important; }
}
</style>
"""
