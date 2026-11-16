"""Two administrator accounts and expiring opaque sessions."""
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Final, Iterator

from pydantic import BaseModel, ConfigDict, Field

from .files import STATE, publish

SESSION_SECONDS: Final = 8 * 60 * 60
HASH_ROUNDS: Final = 600000


class SeedUser(BaseModel):
    model_config = ConfigDict(frozen=True)
    username: str
    salt: str
    password_hash: str


class AdminSeed(BaseModel):
    model_config = ConfigDict(frozen=True)
    users: list[SeedUser] = Field(min_length=2, max_length=2)


class Administrator(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    username: str


def password_hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), HASH_ROUNDS).hex()


@contextmanager
def database() -> Iterator[sqlite3.Connection]:
    STATE.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(STATE / 'admin.sqlite3', timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database() -> None:
    with database() as connection:
        connection.executescript('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                salt TEXT NOT NULL, password_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY, admin_id INTEGER NOT NULL, expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS login_attempts (
                identity TEXT PRIMARY KEY, count INTEGER NOT NULL, started REAL NOT NULL);
        ''')
        if connection.execute('SELECT count(*) FROM admins').fetchone()[0] == 0:
            seed_path = STATE / 'admin-seed.json'
            if not seed_path.exists():
                raise RuntimeError('Administrator seed missing. Run manage.py init-admins first.')
            seed = AdminSeed.model_validate_json(seed_path.read_text(encoding='utf-8'))
            connection.executemany('INSERT INTO admins(username,salt,password_hash) VALUES(?,?,?)',
                                   [(user.username, user.salt, user.password_hash) for user in seed.users])
    (STATE / 'admin.sqlite3').chmod(0o600)


def create_administrator_seed(destination: Path) -> bool:
    """Generate credentials once; existing account material is never overwritten."""
    seed_path = STATE / 'admin-seed.json'
    if seed_path.exists() or (STATE / 'admin.sqlite3').exists():
        return False
    users, lines = [], ['Football Know 管理员账号', '', '请妥善保存，不要上传到网站公开目录。', '']
    for username in ['admin01', 'admin02']:
        password = secrets.token_urlsafe(18)
        salt = secrets.token_hex(16)
        users.append(SeedUser(username=username, salt=salt, password_hash=password_hash(password, salt)))
        lines.extend([f'账号：{username}', f'密码：{password}', ''])
    seed = AdminSeed(users=users)
    STATE.mkdir(parents=True, exist_ok=True)
    STATE.chmod(0o700)
    publish(seed_path, seed.model_dump(mode='json'))
    seed_path.chmod(0o600)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x', encoding='utf-8') as output:
        output.write('\n'.join(lines) + '\n入口：网站菜单中的“管理后台”。\n')
    destination.chmod(0o600)
    return True


def login(username: str, password: str) -> tuple[Administrator, str] | None:
    now = time.time()
    identity = username.lower().strip()
    with database() as connection:
        row = connection.execute('SELECT * FROM admins WHERE username=?', (identity,)).fetchone()
        identity = identity if row else '__unknown__'
        attempt = connection.execute('SELECT count,started FROM login_attempts WHERE identity=?', (identity,)).fetchone()
        if attempt and now - attempt['started'] < 600 and attempt['count'] >= 10:
            return None
        salt = row['salt'] if row else '00' * 16
        expected = row['password_hash'] if row else '00' * 32
        valid = hmac.compare_digest(password_hash(password, salt), expected)
        if not row or not valid:
            count = attempt['count'] + 1 if attempt and now - attempt['started'] < 600 else 1
            started = attempt['started'] if count > 1 else now
            connection.execute('INSERT OR REPLACE INTO login_attempts VALUES(?,?,?)', (identity, count, started))
            return None
        connection.execute('DELETE FROM login_attempts WHERE identity=?', (identity,))
        connection.execute('DELETE FROM sessions WHERE expires<?', (now,))
        token = secrets.token_urlsafe(32)
        connection.execute('INSERT INTO sessions VALUES(?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), row['id'], now + SESSION_SECONDS))
        return Administrator(id=row['id'], username=row['username']), token


def current_admin(token: str | None) -> Administrator | None:
    if not token or len(token) > 100:
        return None
    with database() as connection:
        row = connection.execute('''SELECT admins.id,admins.username FROM admins
            JOIN sessions ON admins.id=sessions.admin_id WHERE token_hash=? AND expires>?''',
            (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
    return Administrator(id=row['id'], username=row['username']) if row else None


def logout(token: str) -> None:
    with database() as connection:
        connection.execute('DELETE FROM sessions WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),))


def change_password(admin: Administrator, passwords: tuple[str, str]) -> bool:
    old, new = passwords
    with database() as connection:
        row = connection.execute('SELECT * FROM admins WHERE id=?', (admin.id,)).fetchone()
        if not row or not hmac.compare_digest(password_hash(old, row['salt']), row['password_hash']):
            return False
        salt = secrets.token_hex(16)
        connection.execute('UPDATE admins SET salt=?,password_hash=? WHERE id=?', (salt, password_hash(new, salt), admin.id))
        connection.execute('DELETE FROM sessions WHERE admin_id=?', (admin.id,))
    return True
