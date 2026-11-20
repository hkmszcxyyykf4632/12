"""Persistent page-open counter. Network retries reuse the same event ID."""
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from uuid import UUID

def counter(event=None, path=None):
    if event is not None:
        event = str(UUID(str(event)))
    if path is None:
        from .files import STATE
        path = STATE / 'visits.sqlite3'
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=10)) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS totals(id INTEGER PRIMARY KEY CHECK(id=1), base INTEGER NOT NULL, added INTEGER NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, day TEXT NOT NULL)')
        db.execute('INSERT OR IGNORE INTO totals VALUES(1,100000,0)')
        if event:
            changed = db.execute('INSERT OR IGNORE INTO events VALUES(?,?)', (event, datetime.now(timezone.utc).date().isoformat())).rowcount
            if changed:
                db.execute('UPDATE totals SET added=added+1 WHERE id=1')
            db.execute("DELETE FROM events WHERE day < date('now','-7 days')")
        base, added = db.execute('SELECT base,added FROM totals WHERE id=1').fetchone()
    return {'total': base + added, 'base': base, 'added': added}
