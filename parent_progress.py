"""Saved-quiz history tools. No list/profile/bookmark writes or live session assumptions."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import time
from threading import Lock
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
import streamlit as st

FEATURE = 'parent_history'
VERSION = 1
HISTORY_CACHE_SECONDS = 60
PROFILE_CACHE_SECONDS = 300
BACKEND_RECHECK_SECONDS = 120
FIELDS = ('id', 'timestamp', 'child_name', 'week_title', 'score', 'total_words', 'mastered', 'unfamiliar')


def _timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        return ZoneInfo('UTC')


def recorded_datetime(record: dict, source_timezone: str = 'Asia/Singapore') -> datetime | None:
    value = record.get('timestamp')
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_timezone(source_timezone))
    return parsed


def time_label(record: dict, display_timezone: str, source_timezone: str = 'Asia/Singapore') -> str:
    date = recorded_datetime(record, source_timezone)
    if date is None:
        return 'Recorded time unavailable'
    local = date.astimezone(_timezone(display_timezone))
    return local.strftime('%d %b %Y, %I:%M %p').replace(', 0', ', ')


def newest_first(records: list[dict], source_timezone: str) -> list[dict]:
    def key(record):
        date = recorded_datetime(record, source_timezone)
        return date.timestamp() if date else float('-inf')
    return sorted(records, key=key, reverse=True)


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
        if not math.isfinite(number) or not number.is_integer() or number < 0:
            return None
        return int(number)
    except (TypeError, ValueError, OverflowError):
        return None


def session_metrics(record: dict) -> dict:
    score = _integer(record.get('score'))
    total = _integer(record.get('total_words'))
    if score is None or total is None or score > total:
        return {'correct': None, 'needs_practice': None, 'total': total, 'accuracy': None, 'valid': False}
    return {'correct': score, 'needs_practice': total - score, 'total': total,
            'accuracy': 100 * score / total if total else None, 'valid': True}


def word_breakdown(value: Any) -> list[str]:
    if not isinstance(value, str) or value.strip().casefold() in {'', 'none', 'n/a'}:
        return []
    return [item.strip() for item in value.replace('，', ',').split(',') if item.strip()]


def child_records(records: list[dict], child_name: str) -> list[dict]:
    wanted = child_name.strip().casefold()
    return [record for record in records if str(record.get('child_name', '')).strip().casefold() == wanted]


def _normalize(data: Any, legacy: bool = False) -> list[dict]:
    if not isinstance(data, list):
        raise ValueError('Invalid history response')
    records = []
    seen = set()
    for index, raw in enumerate(data):
        if not isinstance(raw, dict):
            raise ValueError('Invalid history record')
        record = {key: raw.get(key, '') for key in FIELDS}
        record['child_name'] = str(record['child_name'] or 'Student').strip() or 'Student'
        for key in ('timestamp', 'week_title', 'mastered', 'unfamiliar'):
            record[key] = str(record[key] or '')
        if legacy:
            identity = json.dumps([index, raw], ensure_ascii=False, sort_keys=True, default=str)
            record['id'] = 'legacy:' + hashlib.sha256(identity.encode('utf-8')).hexdigest()
        if not isinstance(record['id'], str) or not record['id'] or record['id'] in seen:
            raise ValueError('Missing or duplicate history ID')
        seen.add(record['id'])
        records.append(record)
    return records


def _get(api_url: str, params: dict) -> Any:
    response = requests.get(api_url, params=params, allow_redirects=True, timeout=15)
    if response.status_code != 200:
        raise requests.RequestException('History service unavailable')
    return response.json()


class _UncachedFailure(Exception):
    """Only successful reads are cached; transient errors remain retryable."""
    def __init__(self, value):
        super().__init__('Parent data could not be loaded')
        self.value = value


@st.cache_resource(show_spinner=False)
def _backend_modes():
    # Capability state only: no history, cookies, or PINs are stored here.
    return {'lock': Lock(), 'legacy_until': {}}


def _known_legacy(api_url: str) -> bool:
    state = _backend_modes()
    with state['lock']:
        until = state['legacy_until'].get(api_url, 0)
        if until <= time.monotonic():
            state['legacy_until'].pop(api_url, None)
            return False
        return True


def _remember_legacy(api_url: str):
    state = _backend_modes()
    with state['lock']:
        if len(state['legacy_until']) >= 128:
            state['legacy_until'].pop(next(iter(state['legacy_until'])), None)
        state['legacy_until'][api_url] = time.monotonic() + BACKEND_RECHECK_SECONDS


def _legacy_time_notice(records):
    for record in records:
        try:
            parsed = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                return 'Historical timestamps without a timezone are interpreted as Asia/Singapore.'
        except (TypeError, ValueError):
            continue
    return None


def _load_history(api_url: str) -> dict:
    result = {'records': [], 'source_timezone': 'Asia/Singapore', 'delete_ready': False,
              'error': None, 'notice': None, 'profiles': None, 'profile_error': None, 'time_notice': None}
    if not api_url:
        result['error'] = 'Google Sheets is not configured. Your saved history has not been deleted.'
        return result
    try:
        data = None if _known_legacy(api_url) else _get(api_url, {'action': 'get_history_records'})
        if isinstance(data, dict) and data.get('feature') == FEATURE and data.get('version') == VERSION:
            if data.get('status') != 'success':
                result['error'] = str(data.get('message') or 'History could not be loaded. Please try again.')
                return result
            result['records'] = _normalize(data.get('history'))
            result['source_timezone'] = str(data.get('timezone') or 'Asia/Singapore')
            try:
                ZoneInfo(result['source_timezone'])
            except (ZoneInfoNotFoundError, ValueError):
                result['source_timezone'] = 'UTC'
                result['time_notice'] = 'The spreadsheet timezone is unsupported; UTC is used for timestamps without timezone information.'
            configured = data.get('delete_configured', True)
            if not isinstance(configured, bool):
                raise ValueError('Invalid deletion configuration response')
            result['delete_ready'] = configured
            if not configured:
                result['notice'] = 'History loaded. To enable deletion, configure PARENT_PIN in the existing Apps Script project to match the private Streamlit parent PIN.'
            if 'profiles' in data:
                names = data['profiles']
                if isinstance(names, list) and all(isinstance(name, str) and name.strip() for name in names):
                    result['profiles'] = list(dict.fromkeys(name.strip() for name in names))
                    result['profile_error'] = data.get('profiles_error')
        else:
            # Remember unsupported capability briefly; do not repeat the failed
            # modern probe on every normal read. Explicit Refresh resets this.
            _remember_legacy(api_url)
            result['records'] = _normalize(_get(api_url, {'action': 'get_history'}), legacy=True)
            result['notice'] = "History loaded in view-only mode. Update the existing Apps Script deployment to enable deletion, then click 'Refresh saved history'."
            result['time_notice'] = _legacy_time_notice(result['records'])
    except (requests.RequestException, ValueError, TypeError, KeyError):
        result['error'] = 'Could not load saved quiz history. This is a connection/response error, not confirmation that any records were deleted.'
    return result


@st.cache_data(ttl=HISTORY_CACHE_SECONDS, max_entries=128, show_spinner=False)
def _cached_history(api_url: str) -> dict:
    result = _load_history(api_url)
    if result['error']:
        raise _UncachedFailure(result)
    return result


def fetch_history(api_url: str) -> dict:
    try:
        return _cached_history(api_url)
    except _UncachedFailure as failure:
        return failure.value


def _clear_history(api_url=None):
    if api_url is None:
        _cached_history.clear()
    else:
        _cached_history.clear(api_url)
    state = _backend_modes()
    with state['lock']:
        if api_url is None:
            state['legacy_until'].clear()
        else:
            state['legacy_until'].pop(api_url, None)


# Retain the old fetch_history.clear(...) API used by existing callers.
fetch_history.clear = _clear_history


@st.cache_data(ttl=PROFILE_CACHE_SECONDS, max_entries=128, show_spinner=False)
def _cached_profiles(api_url: str) -> tuple[list[str], str | None]:
    if not api_url:
        raise _UncachedFailure(([], 'Google Sheets is not configured.'))
    try:
        data = _get(api_url, {'action': 'get_profiles'})
        if isinstance(data, list) and all(isinstance(value, str) and value.strip() for value in data):
            return list(dict.fromkeys(value.strip() for value in data)), None
    except (requests.RequestException, ValueError, TypeError):
        pass
    raise _UncachedFailure(([], 'Could not load learner profiles. Learner names from saved history are shown instead.'))


def fetch_profiles(api_url: str) -> tuple[list[str], str | None]:
    try:
        return _cached_profiles(api_url)
    except _UncachedFailure as failure:
        return failure.value


fetch_profiles.clear = _cached_profiles.clear


def clear_parent_cache(api_url=None):
    fetch_history.clear(api_url)
    if api_url is None:
        fetch_profiles.clear()
    else:
        fetch_profiles.clear(api_url)


def fetch_dashboard(api_url: str) -> dict:
    """Use the combined backend response; old backends retain safe fallback."""
    result = fetch_history(api_url)
    if result['error']:
        return result
    if result['profiles'] is None:
        profiles, error = fetch_profiles(api_url)
        result['profiles'] = profiles
        result['profile_error'] = error
    return result


def snapshot(records: list[dict]) -> str:
    return json.dumps([{key: record.get(key, '') for key in FIELDS} for record in records], ensure_ascii=False, sort_keys=True, default=str)


def delete_records(api_url: str, child_name: str, ids: list[str], parent_pin: str, confirmed: bool = False) -> dict:
    failure = {'error': 'History deletion could not be confirmed. Refresh history before trying again.', 'deleted_ids': [], 'missing_ids': []}
    if not confirmed or not api_url or not parent_pin or not child_name.strip() or not ids or any(not isinstance(value, str) or not value or value.startswith('legacy:') for value in ids):
        failure['error'] = 'A configured parent PIN, child, valid records, and explicit confirmation are required.'
        return failure
    requested = list(dict.fromkeys(ids))
    try:
        response = requests.post(api_url, json={'action': 'delete_history_records', 'child_name': child_name,
            'ids': requested, 'parent_pin': parent_pin, 'confirm_delete': True}, allow_redirects=True, timeout=20)
        data = response.json()
        if response.status_code != 200 or not isinstance(data, dict) or data.get('feature') != FEATURE or data.get('version') != VERSION:
            return failure
        if data.get('status') != 'success':
            failure['error'] = str(data.get('message') or failure['error'])
            return failure
        deleted, missing = data.get('deleted_ids'), data.get('missing_ids')
        if not isinstance(deleted, list) or not isinstance(missing, list) or any(not isinstance(value, str) for value in deleted + missing):
            return failure
        if len(set(deleted + missing)) != len(deleted + missing) or set(deleted + missing) != set(requested):
            return failure
        fetch_history.clear()
        return {'error': None, 'deleted_ids': deleted, 'missing_ids': missing}
    except (requests.RequestException, ValueError, TypeError):
        return failure


def history_csv(records: list[dict], display_timezone: str, source_timezone: str) -> bytes:
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(['Record ID', 'Child', 'Recorded time (' + display_timezone + ')', 'Original timestamp', 'Spelling list', 'Correct', 'Total', 'Correct words', 'Needs-practice words'])
    def safe(value):
        value = str(value)
        return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value
    for record in records:
        writer.writerow([safe(value) for value in [record['id'], record['child_name'], time_label(record, display_timezone, source_timezone),
            record['timestamp'], record['week_title'], record['score'], record['total_words'], record['mastered'], record['unfamiliar']]])
    return ('\ufeff' + output.getvalue()).encode('utf-8')
