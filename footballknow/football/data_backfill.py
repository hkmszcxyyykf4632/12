"""Bounded, durable coverage queues for the complete stock and horse catalogues."""
import json
import math
import re
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from .files import PUBLIC, STATE, publish
from .finance import load, refresh_company
from .sync_control import read_control

FIELDS = {
    'companies': ['profile', 'business', 'holders', 'balance', 'income', 'cashflow'],
    'horse-research': ['workouts', 'sectionals'],
}


@contextmanager
def database():
    STATE.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(STATE / 'data-backfill.sqlite3', timeout=20)
    db.row_factory = sqlite3.Row
    db.execute('''CREATE TABLE IF NOT EXISTS items (
        kind TEXT NOT NULL, ident TEXT NOT NULL, attempted REAL NOT NULL DEFAULT 0,
        due REAL NOT NULL DEFAULT 0, fields TEXT NOT NULL DEFAULT '{}',
        complete INTEGER NOT NULL DEFAULT 0, problem TEXT NOT NULL DEFAULT '',
        PRIMARY KEY(kind,ident))''')
    try:
        with db:
            yield db
    finally:
        db.close()


def detail_path(kind, ident):
    return PUBLIC / ('finance/companies' if kind == 'companies' else 'racing/research') / (ident + '.json')


def coverage(kind, value):
    if kind == 'companies':
        statements = value.get('financials', {}).get('statements', {})
        return {'profile': bool(value.get('profile', {}).get('legalName')),
                'business': bool(value.get('profile', {}).get('business')),
                'holders': bool(value.get('holders', {}).get('rows')),
                **{k: any(isinstance(r.get('amount'), (int, float)) and math.isfinite(r['amount'])
                          for r in statements.get(k, [])) for k in ['balance', 'income', 'cashflow']}}
    # An explicitly parsed empty workout table is still a checked source. A horse
    # without a completed run does not need race sectionals.
    horse = load(PUBLIC / 'racing/horses' / (value.get('horseId', '') + '.json'))
    raced = any(r.get('raceId') and not r.get('withdrawn') for r in horse.get('records', []))
    career = next((str(v) for k, v in horse.get('profile', {}).items() if '總出賽' in k), '')
    unraced = bool(re.fullmatch(r'0\s*-\s*0\s*-\s*0\s*-\s*0', career)) and not raced
    return {'workouts': bool(value.get('workouts', {}).get('fetchedAt')),
            'sectionals': bool(value.get('sectionals')) or unraced}


def catalogue(kind):
    if kind == 'companies':
        return {r['code']: r for name in ['stocks.json', 'cn-stocks.json']
                for r in load(PUBLIC / 'finance' / name).get('stocks', [])}
    if kind == 'horse-research':
        return {r['id']: r for r in load(PUBLIC / 'racing/catalogue.json').get('horses', [])}
    raise ValueError('Unknown backfill queue')


def priority_horses():
    ids = set()
    today = datetime.now(timezone.utc).date().isoformat()
    for race in load(PUBLIC / 'racing/meetings.json').get('races', []):
        if race.get('status') == 'scheduled' and race.get('date', '') >= today:
            full = load(PUBLIC / 'racing/races' / (race['id'] + '.json'))
            ids.update(h['id'] for h in full.get('entries', []) if not h.get('withdrawn'))
    return ids


def initialize(kind, items):
    with database() as db:
        known = {r['ident'] for r in db.execute('SELECT ident FROM items WHERE kind=?', (kind,))}
        for ident in items.keys() - known:
            value = load(detail_path(kind, ident))
            fields = coverage(kind, value) if value else {k: False for k in FIELDS[kind]}
            db.execute('INSERT INTO items(kind,ident,fields,complete) VALUES(?,?,?,?)',
                       (kind, ident, json.dumps(fields), int(all(fields.values()) and
                        not value.get('failedSections' if kind == 'companies' else 'errors'))))


def status(kind, items):
    with database() as db:
        rows = [dict(r) for r in db.execute('SELECT * FROM items WHERE kind=?', (kind,)) if r['ident'] in items]
    fields = [json.loads(r['fields']) for r in rows]
    stamp = datetime.now(timezone.utc).isoformat()
    result = {'updatedAt': stamp, 'kind': kind, 'total': len(items),
              'complete': sum(r['complete'] for r in rows),
              'checked': sum(bool(r['attempted']) for r in rows),
              'withData': sum(any(v.values()) for v in fields),
              'fields': {k: sum(bool(v.get(k)) for v in fields) for k in FIELDS[kind]},
              'retrying': sum(bool(r['problem']) for r in rows),
              'paused': not read_control()['enabled']}
    publish(PUBLIC / ('finance' if kind == 'companies' else 'racing') / 'backfill-status.json', result)
    return result


def refresh(kind, limit=24, budget_seconds=180):
    items = catalogue(kind)
    if not items:
        raise ValueError('Backfill catalogue unavailable')
    initialize(kind, items)
    started = time.monotonic()
    priority = priority_horses() if kind == 'horse-research' else set()
    with database() as db:
        rows = [dict(r) for r in db.execute('SELECT * FROM items WHERE kind=? AND due<=?', (kind, time.time())) if r['ident'] in items]
    rows.sort(key=lambda r: (r['ident'] not in priority, r['complete'], r['attempted'], r['ident']))
    attempted = succeeded = 0
    for row in rows[:max(1, min(limit, 100))]:
        if not read_control()['enabled'] or time.monotonic() - started >= budget_seconds:
            break
        ident, at = row['ident'], time.time()
        with database() as db:
            claimed = db.execute('UPDATE items SET due=? WHERE kind=? AND ident=? AND due<=?',
                                 (at + 1800, kind, ident, at)).rowcount
        if not claimed:
            continue
        attempted += 1
        problem = ''
        try:
            if kind == 'companies':
                refresh_company(ident)
            else:
                from .racing import horse_detail
                from .horse_research import refresh as refresh_research
                horse_detail(ident)
                refresh_research(ident)
            value = load(detail_path(kind, ident))
            if value.get('code' if kind == 'companies' else 'horseId') != ident:
                raise ValueError('Detail identity missing or mismatched')
            fields = coverage(kind, value)
            complete = all(fields.values()) and not value.get('failedSections' if kind == 'companies' else 'errors')
            problem = '' if complete else '部分来源字段尚未完整，保留已取得资料并重试'
            succeeded += int(complete)
        except (OSError, ValueError, KeyError, TypeError):
            fields, complete = json.loads(row['fields']), False
            problem = '来源读取或身份核对未成功，保留最近资料并重试'
        delay = (7 * 86400 if kind == 'companies' else 86400) if complete else 6 * 3600
        with database() as db:
            db.execute('UPDATE items SET attempted=?,due=?,fields=?,complete=?,problem=? WHERE kind=? AND ident=?',
                       (at, time.time() + delay, json.dumps(fields), int(complete), problem, kind, ident))
    result = status(kind, items)
    if kind == 'companies' and attempted:
        from .capital_structure import refresh_capital_index
        refresh_capital_index()
    return {**result, 'attemptedThisRun': attempted, 'completedThisRun': succeeded}
