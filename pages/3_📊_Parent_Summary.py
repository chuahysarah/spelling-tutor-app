from __future__ import annotations

import hmac
import sys
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from practice_bookmarks import apply_practice_theme
from parent_progress import (
    child_records, delete_records, fetch_history, fetch_profiles, fetch_dashboard, clear_parent_cache, history_csv,
    newest_first, recorded_datetime, session_metrics, snapshot, time_label, word_breakdown,
)

st.set_page_config(page_title="Track your child's progress", page_icon="📊", layout="centered", initial_sidebar_state="auto")
st.sidebar.page_link('app.py', label='Home')
st.sidebar.page_link('pages/1_📖_Learn_Words.py', label='Learn Words', icon='📖')
st.sidebar.page_link('pages/2_🎯_Dictation_Quiz.py', label='Dictation Quiz', icon='🎯')
st.sidebar.page_link('pages/5_More_Practices.py', label='Bookmarks', icon='🔖')
st.sidebar.page_link('pages/4_🌱_Word Garden.py', label='Word Garden', icon='🌱')
st.sidebar.page_link('pages/3_📊_Parent_Summary.py', label='Parent Summary', icon='📊')
st.sidebar.divider()
apply_practice_theme()
st.markdown("""
<style>
[data-testid="stMainBlockContainer"] { max-width:1120px; padding-top:4.75rem; }
[data-testid="stMarkdownContainer"] h1 { font-size:clamp(1.75rem,4vw,2.5rem) !important; }
.progress-session { padding:1.2rem 1.4rem; border:2px solid #a6c1e5; border-radius:22px;
    background:linear-gradient(110deg,#e6f4ff,#f0eaff); margin:.8rem 0 1rem; }
.progress-session .eyebrow { color:#4b1d82 !important; font-size:.95rem; font-weight:800; letter-spacing:.04em; }
.progress-session h3 { margin:.3rem 0; color:#173f91 !important; }
.progress-session p { margin:.25rem 0; color:#1f2937 !important; }
.progress-card { min-height:155px; padding:1.2rem; border:2px solid #64748b; border-radius:22px;
    background:#fff; box-shadow:0 6px 18px rgba(23,63,145,.08); }
.progress-card.correct { background:linear-gradient(140deg,#fff,#e3f6ed); border-color:#287153; }
.progress-card.practice { background:linear-gradient(140deg,#fff,#fff0d4); border-color:#9a5b09; }
.progress-card.accuracy { background:linear-gradient(140deg,#fff,#e6efff); border-color:#173f91; }
.progress-card .card-label { color:#1f2937 !important; font-weight:800; font-size:1.05rem; }
.progress-card .card-value { color:#111827 !important; font:800 2.6rem/1.2 'Baloo 2','Trebuchet MS',sans-serif; margin:.45rem 0; }
.progress-card .card-note { color:#374151 !important; font-size:.95rem; }
.word-chips { display:flex; flex-wrap:wrap; gap:.5rem; }
.word-chip { display:inline-block; background:#eff6ff; border:1px solid #64748b; border-radius:12px;
    padding:.35rem .65rem; color:#173f91; font-weight:700; overflow-wrap:anywhere; }
.st-key-progress_overview [data-testid="stHorizontalBlock"] { gap:.8rem; }
.st-key-progress_history [data-testid="stExpander"] summary p { font:800 1.05rem 'Nunito',Arial,sans-serif !important; }
[data-testid="stTabs"] [role="tab"] { min-height:48px; font-weight:800; }
[data-testid="stTabs"] [role="tab"] p { font-size:1rem !important; }
.st-key-progress_delete_selected button, .st-key-progress_clear_all button,
.st-key-progress_confirm_delete button { background:#a12626 !important; border-color:#7c1d1d !important; }
:is(.st-key-progress_delete_selected,.st-key-progress_clear_all,.st-key-progress_confirm_delete) button:hover:not(:disabled) { background:#7c1d1d !important; border-color:#7c1d1d !important; }
.st-key-progress_delete_selected button:disabled, .st-key-progress_clear_all button:disabled,
.st-key-progress_confirm_delete button:disabled { background:#e5e7eb !important; border-color:#64748b !important; }
@media(max-width:640px) {
    .st-key-progress_overview [data-testid="stHorizontalBlock"] { flex-direction:column !important; }
    .st-key-progress_overview [data-testid="stColumn"] { width:100% !important; min-width:100% !important; }
    .progress-card { min-height:120px; padding:1rem; margin-bottom:12px; }
    .progress-card .card-value { font-size:2.2rem; }
    .progress-session { padding:1rem; }
    [data-testid="stTabs"] [role="tablist"] { gap:.25rem; }
    [data-testid="stTabs"] [role="tab"] { padding:.4rem .6rem; }
}
</style>
""", unsafe_allow_html=True)

st.title("Track your child's progress")
st.caption('Saved quiz results and history tools for parents.')
API_URL = str(st.secrets.get('GSHEETS_API_URL', '')).strip()
PARENT_PIN = str(st.secrets.get('PARENT_PIN', '')).strip()
if not PARENT_PIN:
    st.warning('Configure a private PARENT_PIN in Streamlit Secrets and the matching Apps Script property before using this parent page. Do not share the PIN in chat.')
    st.stop()

if not st.session_state.get('parent_dashboard_unlocked') or not hmac.compare_digest(str(st.session_state.get('history_parent_pin', '')).encode(), PARENT_PIN.encode()):
    st.session_state.parent_dashboard_unlocked = False
    st.info('Parents only: enter your private parent PIN to view and manage saved history.')
    entered = st.text_input('Parent PIN', type='password', key='dash_pin_entry')
    if entered and hmac.compare_digest(entered.encode(), PARENT_PIN.encode()):
        st.session_state.parent_dashboard_unlocked = True
        st.session_state.history_parent_pin = entered
        st.rerun()
    elif entered:
        st.error('Incorrect parent PIN.')
    st.stop()


def lock_dashboard():
    st.session_state.parent_dashboard_unlocked = False
    for key in ('history_parent_pin', 'history_delete_plan', 'dash_pin_entry'):
        st.session_state.pop(key, None)


with st.sidebar:
    st.caption('Parent history tools')
    st.button('Lock dashboard', key='progress_lock', on_click=lock_dashboard, use_container_width=True)
    if st.button('Refresh saved history', key='progress_refresh', use_container_width=True):
        clear_parent_cache(API_URL)
        st.session_state.pop('history_delete_plan', None)
        st.rerun()
    st.caption('History reads are cached for up to 60 seconds. Refresh bypasses the cache.')

with st.spinner('Loading saved quiz results…'):
    loaded = fetch_dashboard(API_URL)
if loaded['error']:
    st.error(loaded['error'])
    st.stop()
if loaded['notice']:
    st.info(loaded['notice'])
if loaded.get('time_notice'):
    st.caption(loaded['time_notice'])
records = loaded['records']
source_zone = loaded['source_timezone']
profiles, profile_error = loaded['profiles'], loaded['profile_error']
if profile_error:
    st.warning(profile_error)
children = list(dict.fromkeys(profiles + [record['child_name'] for record in records]))
if not children:
    st.info('No learner profiles or saved quiz records could be found. This page does not create or replace learner profiles.')
    st.stop()
initial = st.session_state.get('active_child')
if st.session_state.get('progress_child') not in children:
    st.session_state.progress_child = initial if initial in children else children[0]
child = st.selectbox('Child whose history is shown:', children, key='progress_child')
zones = list(dict.fromkeys(['Asia/Singapore', source_zone, 'Asia/Kuala_Lumpur', 'Asia/Hong_Kong', 'UTC']))
if st.session_state.get('progress_timezone') not in zones:
    st.session_state.progress_timezone = zones[0]
with st.sidebar:
    display_zone = st.selectbox('Display timezone:', zones, key='progress_timezone')
st.caption('Times shown in ' + display_zone + '. Change the timezone in the menu.')
if st.session_state.get('history_delete_plan', {}).get('child_name') not in (None, child):
    st.session_state.pop('history_delete_plan', None)
view = newest_first(child_records(records, child), source_zone)
if 'progress_feedback' in st.session_state:
    st.success(st.session_state.pop('progress_feedback'))


def card(kind: str, label: str, value, note: str):
    st.markdown('<div class="progress-card ' + kind + '"><div class="card-label">' + escape(label) +
        '</div><div class="card-value">' + escape(str(value)) + '</div><div class="card-note">' + escape(note) + '</div></div>', unsafe_allow_html=True)


def show_words(label: str, words: list[str]):
    with st.expander(label, expanded=False):
        if words:
            st.markdown('<div class="word-chips">' + ''.join('<span class="word-chip">' + escape(word) + '</span>' for word in words) + '</div>', unsafe_allow_html=True)
        else:
            st.caption('No word breakdown was saved for this category.')


def stage_delete(items: list[dict], mode: str):
    st.session_state.history_delete_plan = {'child_name': child, 'mode': mode, 'records': items, 'ids': [item['id'] for item in items]}
    st.session_state.pop('progress_confirm_name', None)
    st.session_state.pop('progress_confirm_ack', None)


overview_tab, trend_tab, history_tab = st.tabs(['Saved quiz', 'Progress', 'History'])
with overview_tab:
    st.subheader('Saved quiz overview for ' + child)
    st.caption('Saved quiz results—not browser-session counters. Latest by default; choose an earlier quiz below. A quiz in progress appears only after it is saved.')
    if not view:
        st.info('No saved quiz records for ' + child + ' yet. There is no dated saved session to display.')
    else:
        ids = [record['id'] for record in view]
        by_id = {record['id']: record for record in view}
        session_key = 'progress_session_' + child
        if st.session_state.get(session_key) not in ids:
            st.session_state[session_key] = ids[0]
        def session_option(record_id):
            position = ids.index(record_id)
            record = by_id[record_id]
            prefix = 'Latest saved · ' if position == 0 and recorded_datetime(record, source_zone) else 'Record ' + str(position + 1) + ' · '
            return prefix + time_label(record, display_zone, source_zone) + ' · ' + record['week_title']
        chosen_id = st.selectbox('Choose a saved quiz:', ids, format_func=session_option, key=session_key)
        chosen = by_id[chosen_id]
        st.markdown('<div class="progress-session"><div class="eyebrow">SELECTED SAVED QUIZ</div><h3>' + escape(chosen['week_title'] or 'Untitled spelling list') +
            '</h3><p><strong>Recorded:</strong> ' + escape(time_label(chosen, display_zone, source_zone)) + ' · ' + escape(display_zone) + '</p></div>', unsafe_allow_html=True)
        metrics = session_metrics(chosen)
        with st.container(key='progress_overview'):
            correct, practice, accuracy = st.columns(3)
            with correct:
                card('correct', 'Correct answers', metrics['correct'] if metrics['correct'] is not None else '—', 'Saved score out of ' + str(metrics['total']) if metrics['valid'] else 'Score unavailable or invalid')
            with practice:
                card('practice', 'Needs practice', metrics['needs_practice'] if metrics['needs_practice'] is not None else '—', 'Incorrect answers in this quiz')
            with accuracy:
                card('accuracy', 'Accuracy', f"{metrics['accuracy']:.0f}%" if metrics['accuracy'] is not None else '—', 'For this selected saved quiz only')
        if metrics['accuracy'] is not None:
            st.progress(metrics['accuracy'] / 100, text=f"{metrics['correct']} correct of {metrics['total']} scored items")
        elif not metrics['valid']:
            st.warning('This record has missing or invalid score values; it is excluded from progress calculations.')
        else:
            st.caption('This record has no scored items, so an accuracy percentage cannot be calculated.')
        show_words('View correct words', word_breakdown(chosen['mastered']))
        show_words('View words needing practice', word_breakdown(chosen['unfamiliar']))

with trend_tab:
    st.subheader('Progress across saved quizzes')
    st.caption('These totals cover all saved records for ' + child + ', not just the quiz selected above.')
    valid = [(record, session_metrics(record)) for record in view if session_metrics(record)['valid']]
    correct_sum = sum(metrics['correct'] for _, metrics in valid)
    total_sum = sum(metrics['total'] for _, metrics in valid)
    a, b = st.columns(2)
    with a:
        st.metric('Saved quizzes', len(view))
    with b:
        st.metric('Overall correct-answer rate', f'{100 * correct_sum / total_sum:.0f}%' if total_sum else '—')
    st.caption('Overall rate = correct answers ÷ scored items across valid saved quizzes. Invalid scores are excluded.')
    chart_rows = []
    for record, metrics in reversed(valid):
        if metrics['accuracy'] is not None and recorded_datetime(record, source_zone):
            chart_rows.append({'When': time_label(record, display_zone, source_zone), 'Accuracy (%)': metrics['accuracy'],
                'Spelling list': record['week_title'], 'Score': f"{metrics['correct']}/{metrics['total']}", 'Record': record['id'][-6:]})
    if chart_rows:
        frame = pd.DataFrame(chart_rows)
        ordered = list(dict.fromkeys(row['When'] for row in chart_rows))
        chart = alt.Chart(frame).mark_line(point=True, color='#173f91').encode(
            x=alt.X('When:N', sort=ordered, title='Recorded time (' + display_zone + ')', axis=alt.Axis(labelAngle=-15, labelLimit=220)),
            y=alt.Y('Accuracy (%):Q', scale=alt.Scale(domain=[0, 100])),
            tooltip=['When:N', 'Spelling list:N', 'Score:N', alt.Tooltip('Accuracy (%):Q', format='.1f'), 'Record:N'],
        ).configure_axis(labelFont='Nunito', titleFont='Nunito', labelColor='#1f2937', titleColor='#1f2937', gridColor='#e2e8f0')
        st.altair_chart(chart, use_container_width=True)
        st.caption('Hover or tap a point to inspect its saved quiz details. Records without a usable date cannot be placed on this timeline.')
    else:
        st.info('There are no dated, scored quizzes to plot yet.')

with history_tab:
    st.subheader('History log for ' + child)
    st.caption('Each row is a separate saved quiz record. Tick specific records to remove, or clear all saved history for this selected child.')
    if not view:
        st.info('No saved history for this child.')
    else:
        st.download_button('Download this child’s history CSV', history_csv(view, display_zone, source_zone), file_name='quiz_history.csv', mime='text/csv', key='progress_export')
        lists = [None] + sorted({record['week_title'] for record in view})
        filter_key = 'progress_list_filter_' + child
        if st.session_state.get(filter_key) not in lists:
            st.session_state[filter_key] = None
        selected_list = st.selectbox('Filter by spelling list:', lists, format_func=lambda value: 'All spelling lists' if value is None else value, key=filter_key)
        visible = [record for record in view if selected_list is None or record['week_title'] == selected_list]
        known_dates = [recorded_datetime(record, source_zone).astimezone(ZoneInfo(display_zone)).date() for record in view if recorded_datetime(record, source_zone)]
        if st.checkbox('Filter by date', key='progress_date_filter_' + child, disabled=not known_dates):
            date_range = st.date_input('Recorded date range:', value=(min(known_dates), max(known_dates)), key='progress_dates_' + child)
            if len(date_range) == 2:
                visible = [record for record in visible if recorded_datetime(record, source_zone) and date_range[0] <= recorded_datetime(record, source_zone).astimezone(ZoneInfo(display_zone)).date() <= date_range[1]]
            else:
                st.info('Choose both the start and end date. No records are selected by an incomplete range.')
                visible = []
        st.caption(f'Showing {len(visible)} of {len(view)} saved records for {child}.')
        selected = []
        with st.container(key='progress_history'):
            for number, record in enumerate(visible, start=1):
                label = time_label(record, display_zone, source_zone) + ' · ' + (record['week_title'] or 'Untitled list') + ' · ' + str(record['score']) + '/' + str(record['total_words'])
                with st.container(border=True):
                    if st.checkbox('Select record ' + str(number) + ': ' + label, key='history_pick_' + child + '_' + record['id'], disabled=not loaded['delete_ready']):
                        selected.append(record)
                    with st.expander('View this quiz’s word details'):
                        st.write('Correct words: ' + (record['mastered'] or 'Not recorded'))
                        st.write('Words needing practice: ' + (record['unfamiliar'] or 'Not recorded'))
                        st.caption('Record ID: ' + record['id'])
        delete_col, all_col = st.columns(2)
        with delete_col:
            st.button(f'Review deletion of {len(selected)} selected record(s)', key='progress_delete_selected', disabled=not loaded['delete_ready'] or not selected,
                use_container_width=True, on_click=stage_delete, args=(selected, 'selected'))
        with all_col:
            st.button('Review clearing all ' + str(len(view)) + ' records for ' + child, key='progress_clear_all', disabled=not loaded['delete_ready'],
                use_container_width=True, on_click=stage_delete, args=(view, 'all'))
        st.caption('Clear all includes this child’s records hidden by filters, but never another child’s records. New records added after the confirmation preview are not included.')
        plan = st.session_state.get('history_delete_plan')
        if plan and plan['child_name'] == child:
            with st.container(border=True):
                st.warning('Confirm deletion of ' + str(len(plan['ids'])) + ' saved quiz record(s) for ' + child + '. This cannot be undone in the app. Word Garden totals may decrease because they are calculated from saved history. Spelling lists and bookmarks are not deleted.')
                for record in plan['records']:
                    st.write('• ' + time_label(record, display_zone, source_zone) + ' · ' + record['week_title'] + ' · ' + str(record['score']) + '/' + str(record['total_words']) + ' · Record ID: ' + record['id'])
                typed = st.text_input('Type the child’s name to confirm:', key='progress_confirm_name')
                acknowledged = st.checkbox('I understand the selected history will be permanently removed and garden totals may change.', key='progress_confirm_ack')
                confirm_col, cancel_col = st.columns(2)
                with cancel_col:
                    if st.button('Cancel deletion', key='progress_cancel_delete', use_container_width=True):
                        st.session_state.pop('history_delete_plan', None)
                        st.rerun()
                with confirm_col:
                    if st.button('Permanently delete these records', key='progress_confirm_delete', disabled=not acknowledged or typed != child,
                            use_container_width=True):
                        # Recheck uncached history. Never expand the deletion payload to include unseen new rows.
                        fetch_history.clear(API_URL)
                        fresh = fetch_history(API_URL)
                        fresh_map = {record['id']: record for record in fresh['records']}
                        unchanged = not fresh['error'] and fresh['delete_ready'] and all(record['id'] in fresh_map and snapshot([record]) == snapshot([fresh_map[record['id']]]) for record in plan['records'])
                        if not unchanged:
                            st.session_state.pop('history_delete_plan', None)
                            st.error('History changed or could not be refreshed after the preview. No deletion was sent. Refresh and review the records again.')
                        else:
                            result = delete_records(API_URL, child, plan['ids'], st.session_state.history_parent_pin, confirmed=True)
                            if result['error']:
                                st.error(result['error'])
                            else:
                                st.cache_data.clear()
                                st.session_state.pop('history_delete_plan', None)
                                st.session_state.progress_feedback = 'Deleted ' + str(len(result['deleted_ids'])) + ' saved quiz record(s) for ' + child + '. Spelling lists and bookmarks were not removed.'
                                st.rerun()
