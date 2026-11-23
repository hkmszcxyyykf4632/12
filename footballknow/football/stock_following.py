"""Private stock lists shared only by explicitly paired browser devices."""
from contextlib import closing, contextmanager
import hashlib
import re
import secrets
import sqlite3
import time
from uuid import UUID
from .files import STATE

PATH = STATE / 'stock-following.sqlite3'
MAX_CODES = 10000
PAIR_SECONDS = 600


def _hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


@contextmanager
def _db():
    PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(PATH, timeout=10)) as db, db:
        db.row_factory = sqlite3.Row
        db.executescript('''
        CREATE TABLE IF NOT EXISTS lists(id TEXT PRIMARY KEY, revision INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS devices(token_hash TEXT PRIMARY KEY, list_id TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS stocks(list_id TEXT NOT NULL, code TEXT NOT NULL, PRIMARY KEY(list_id,code));
        CREATE TABLE IF NOT EXISTS operations(list_id TEXT NOT NULL, id TEXT NOT NULL, PRIMARY KEY(list_id,id));
        CREATE TABLE IF NOT EXISTS pairs(code_hash TEXT PRIMARY KEY, list_id TEXT NOT NULL, expires INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts(token_hash TEXT PRIMARY KEY, count INTEGER NOT NULL, started INTEGER NOT NULL);
        ''')
        db.execute('BEGIN IMMEDIATE')
        yield db


def _identity(db, token):
    if not token or len(token) > 100:
        raise PermissionError('同步连接已失效，请刷新页面重新连接。')
    row = db.execute('SELECT list_id FROM devices WHERE token_hash=?', (_hash(token),)).fetchone()
    if not row:
        raise PermissionError('同步连接已失效，请刷新页面重新连接。')
    return row['list_id']


def _state(db, ident, token):
    return {'id': ident, 'device': _hash(token)[:16], 'revision': db.execute('SELECT revision FROM lists WHERE id=?', (ident,)).fetchone()[0],
            'codes': [r[0] for r in db.execute('SELECT code FROM stocks WHERE list_id=? ORDER BY code', (ident,))],
            'devices': db.execute('SELECT count(*) FROM devices WHERE list_id=?', (ident,)).fetchone()[0]}


def connect(token=None):
    with _db() as db:
        try:
            ident = _identity(db, token)
        except PermissionError:
            token = secrets.token_urlsafe(32)
            ident = secrets.token_hex(16)
            db.execute('INSERT INTO lists(id) VALUES(?)', (ident,))
            db.execute('INSERT INTO devices VALUES(?,?)', (_hash(token), ident))
        return _state(db, ident, token), token


def apply(token, changes):
    if len(changes) > 200:
        raise ValueError('单次更改数量过多。')
    for change in changes:
        UUID(change['id'])
        if not re.fullmatch(r'\d{5,6}', change['code']) or type(change['following']) is not bool:
            raise ValueError('股票关注格式不正确。')
    with _db() as db:
        ident = _identity(db, token)
        for change in changes:
            inserted = db.execute('INSERT OR IGNORE INTO operations VALUES(?,?)', (ident, change['id'])).rowcount
            if not inserted:
                continue
            if change['following']:
                db.execute('INSERT OR IGNORE INTO stocks VALUES(?,?)', (ident, change['code']))
            else:
                db.execute('DELETE FROM stocks WHERE list_id=? AND code=?', (ident, change['code']))
            db.execute('UPDATE lists SET revision=revision+1 WHERE id=?', (ident,))
        if db.execute('SELECT count(*) FROM stocks WHERE list_id=?', (ident,)).fetchone()[0] > MAX_CODES:
            raise ValueError('关注名单超过一万只，未保存本次更改。')
        return _state(db, ident, token)


def make_pair(token):
    with _db() as db:
        ident = _identity(db, token)
        now = int(time.time())
        code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(12))
        db.execute('DELETE FROM pairs WHERE list_id=? OR expires<=?', (ident, now))
        db.execute('INSERT INTO pairs VALUES(?,?,?)', (_hash(code), ident, now + PAIR_SECONDS))
        return {'code': '-'.join(code[i:i+4] for i in range(0,12,4)), 'expiresAt': now + PAIR_SECONDS}


def join_pair(token, code):
    code = re.sub(r'[-\s]', '', code).upper()
    error = None
    with _db() as db:
        source = _identity(db, token)
        key, now = _hash(token), int(time.time())
        attempt = db.execute('SELECT count,started FROM attempts WHERE token_hash=?', (key,)).fetchone()
        if attempt and now-attempt['started'] < 600 and attempt['count'] >= 10:
            raise ValueError('同步码多次不正确，请十分钟后重试。')
        pair = db.execute('SELECT list_id FROM pairs WHERE code_hash=? AND expires>?', (_hash(code), now)).fetchone()
        if not pair:
            count = attempt['count']+1 if attempt and now-attempt['started']<600 else 1
            started = attempt['started'] if count>1 else now
            db.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?)', (key, count, started))
            error = '同步码不正确、已使用或已过期，请在另一台设备重新生成。'
        else:
            target = pair['list_id']
            if source != target:
                db.execute('INSERT OR IGNORE INTO stocks SELECT ?,code FROM stocks WHERE list_id=?', (target, source))
                if db.execute('SELECT count(*) FROM stocks WHERE list_id=?', (target,)).fetchone()[0] > MAX_CODES:
                    raise ValueError('合并后关注数量超过一万只，原名单均已保留。')
                db.execute('INSERT OR IGNORE INTO operations SELECT ?,id FROM operations WHERE list_id=?', (target, source))
                db.execute('UPDATE devices SET list_id=? WHERE list_id=?', (target, source))
                db.execute('UPDATE lists SET revision=revision+1 WHERE id=?', (target,))
            db.execute('DELETE FROM pairs WHERE list_id IN (?,?)', (source, target))
            db.execute('DELETE FROM attempts WHERE token_hash=?', (key,))
            result = _state(db, target, token)
    if error:
        raise ValueError(error)
    return result
