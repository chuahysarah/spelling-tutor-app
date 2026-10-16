from __future__ import annotations

import sys
from pathlib import Path
from html import escape

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from practice_bookmarks import (
    apply_practice_theme,
    clear_saved_practice,
    fetch_bookmarks,
    fetch_lists,
    fetch_profiles,
    open_saved_practice,
    parse_list_items,
    show_bookmark_feedback,
)

st.set_page_config(page_title="More Practices!", layout="centered", initial_sidebar_state="auto")

# Fixed sidebar labels/order; keep deployed filenames and app.py unchanged.
st.sidebar.page_link('app.py', label='Home')
st.sidebar.page_link('pages/1_📖_Learn_Words.py', label='Learn Words', icon='📖')
st.sidebar.page_link('pages/2_🎯_Dictation_Quiz.py', label='Dictation Quiz', icon='🎯')
st.sidebar.page_link('pages/5_More_Practices.py', label='More Practices')
st.sidebar.page_link('pages/4_🌱_Word Garden.py', label='Word Garden', icon='🌱')
st.sidebar.page_link('pages/3_📊_Parent_Summary.py', label='Parent Summary', icon='📊')
st.sidebar.divider()
apply_practice_theme()
API_URL = str(st.secrets.get("GSHEETS_API_URL", "")).strip()

if "children" not in st.session_state:
    st.session_state.children = fetch_profiles(API_URL)
if "active_child" not in st.session_state or st.session_state.active_child not in st.session_state.children:
    st.session_state.active_child = st.session_state.children[0]

with st.sidebar:
    st.subheader("Practicing Learner")
    selected_child = st.selectbox(
        "Current Child:",
        options=st.session_state.children,
        index=st.session_state.children.index(st.session_state.active_child),
    )
    if selected_child != st.session_state.active_child:
        st.session_state.active_child = selected_child
        st.rerun()
    if st.button("Back to Learn Words", use_container_width=True):
        st.switch_page("pages/1_📖_Learn_Words.py")

child = st.session_state.active_child
st.markdown(
    '<div class="hero"><h1>More Practices!</h1><p>Saved items for '
    '<span class="child-name">' + escape(str(child)) + '</span></p></div>',
    unsafe_allow_html=True,
)
st.write("Choose a saved item to practise again. When it feels familiar, tap Clear.")
st.caption("Clear removes only the bookmark. It does not delete words from your spelling lists or change quiz scores.")
show_bookmark_feedback(child)

if st.button("Refresh saved items", key="refresh_practices", use_container_width=True):
    fetch_bookmarks.clear()
    fetch_lists.clear()
    st.rerun()

records, error = fetch_bookmarks(API_URL, child)
if error:
    st.warning(error)
    st.stop()
if not records:
    st.info("No saved items yet. In Learn Words, tick Save this item to More Practices! on an item you want to revisit.")
    if st.button("Choose an item in Learn Words", use_container_width=True):
        st.switch_page("pages/1_📖_Learn_Words.py")
    st.stop()

st.write(f"**{len(records)} saved item{'s' if len(records) != 1 else ''}**")
all_lists = "All spelling lists"
list_titles = sorted({record["list_title"] for record in records})
# Use a sentinel outside the real list-title domain, even if a list has this name.
filter_options = [None] + list_titles
filter_key = f"practice_list_filter_{child}"
if st.session_state.get(filter_key) not in filter_options:
    st.session_state[filter_key] = None
selected_list = st.selectbox(
    "Spelling list:", options=filter_options, key=filter_key,
    format_func=lambda title: all_lists if title is None else title,
)
visible = [record for record in records if selected_list is None or record["list_title"] == selected_list]
by_id = {record["id"]: record for record in visible}
ids = list(by_id)
selection_key = f"practice_item_selection_{child}"
if st.session_state.get(selection_key) not in by_id:
    st.session_state[selection_key] = ids[0]
selected_id = st.selectbox(
    "Choose a saved item:", options=ids, index=0, key=selection_key,
    format_func=lambda bookmark_id: by_id[bookmark_id]["word"] + " — " + by_id[bookmark_id]["list_title"],
)
record = by_id[selected_id]
st.markdown("## " + escape(record["word"]), unsafe_allow_html=True)
st.write("**From spelling list:** " + record["list_title"])

available_lists, list_error = fetch_lists(API_URL, child)
can_practise = not list_error and record["word"] in parse_list_items(available_lists.get(record["list_title"], ""))
if list_error:
    st.caption(list_error)
elif not can_practise:
    st.info("This item is no longer in the current spelling list. Its saved text stays here. Clear removes only this bookmark.")

with st.container(key="learn_item_navigation"):
    practice_col, clear_col = st.columns(2, gap="small")
    with practice_col:
        if st.button("Practise this item", key="practise_saved_item", disabled=not can_practise, use_container_width=True):
            open_saved_practice(child, record, available_lists)
    with clear_col:
        st.button(
            "Clear", key="clear_saved_item", use_container_width=True,
            on_click=clear_saved_practice, args=(API_URL, child, record["id"]),
            help="Remove only this saved item from More Practices. You can bookmark it again later.",
        )
