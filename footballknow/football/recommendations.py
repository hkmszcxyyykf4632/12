"""Append-only recommendations and live settlement against their original versions."""
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pydantic import JsonValue
from .files import STATE
from .recommendation_candidates import Candidate, football_candidates, racing_candidates
from .football_statistics import read_statistics as football_statistics
from .racing_statistics import read_statistics as racing_statistics

HONG_KONG = timezone(timedelta(hours=8))
METHOD = 'evidence-priority-v1'
METHOD_TEXT = ('足球每个联赛及欧冠每轮最多三场，赛马每个赛马日一场。只筛选尚未开赛且已保存预测的比赛。'
               '足球比较往绩样本、正式首发、泊松基线对亚洲盘的支持及比分一致性；赛马比较资料覆盖、首选报价的市场支持、晨操证据和报价时效。'
               '排序不是经校准的胜率，不等同保证命中。发布后保留原版本，不因输赢替换；不足合格场次不凑数。')


def initialize(db: sqlite3.Connection) -> None:
    db.execute('''CREATE TABLE IF NOT EXISTS selections (
        domain TEXT NOT NULL, group_key TEXT NOT NULL, event TEXT NOT NULL,
        published_at TEXT NOT NULL, candidate TEXT NOT NULL,
        PRIMARY KEY(domain,event))''')
    db.execute("""CREATE TRIGGER IF NOT EXISTS selection_no_update BEFORE UPDATE ON selections
        BEGIN SELECT RAISE(ABORT, 'Recommendations are immutable'); END""")
    db.execute("""CREATE TRIGGER IF NOT EXISTS selection_no_delete BEFORE DELETE ON selections
        BEGIN SELECT RAISE(ABORT, 'Recommendations are immutable'); END""")


def publish_candidates(candidates: list[Candidate], at: datetime) -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    count = 0
    groups: dict[tuple[str, str], list[Candidate]] = {}
    for c in candidates:
        if c.domain == 'racing' and (c.kickoff.astimezone(HONG_KONG).date() - at.astimezone(HONG_KONG).date()).days > 1:
            continue
        if c.issuedAt <= at < c.kickoff and c.receipt.get('status') == 'pending':
            groups.setdefault((c.domain, c.group), []).append(c)
    with closing(sqlite3.connect(STATE / 'recommendations.sqlite3', timeout=15)) as db:
        initialize(db)
        db.execute('BEGIN IMMEDIATE')
        try:
            for (domain, group), options in groups.items():
                existing = {r[0] for r in db.execute('SELECT event FROM selections WHERE domain=? AND group_key=?', (domain, group))}
                limit = 3 if domain == 'football' else 1
                vacancies = limit - len(existing)
                if vacancies <= 0:
                    continue
                options = sorted((c for c in options if c.event not in existing), key=lambda c: (-c.priority, c.kickoff, c.event))
                if not options:
                    continue
                # Football waits for comparable reports; racing opens on the previous Hong Kong calendar day.
                if domain == 'football' and not existing and min(c.kickoff for c in options).timestamp() - at.timestamp() > 7200:
                    continue
                for c in options[:vacancies]:
                    count += db.execute('INSERT OR IGNORE INTO selections VALUES(?,?,?,?,?)',
                        (domain, group, c.event, at.isoformat(), c.model_dump_json())).rowcount
            db.commit()
        except sqlite3.Error:
            db.rollback()
            raise
    return count


def refresh() -> int:
    at = datetime.now(timezone.utc)
    candidates = football_candidates(at) + racing_candidates(at)
    # Never publish if generation or validation has crossed a kickoff boundary.
    return publish_candidates(candidates, datetime.now(timezone.utc))


def read_recommendations() -> dict[str, JsonValue]:
    at = datetime.now(timezone.utc).isoformat()
    path = STATE / 'recommendations.sqlite3'
    if not path.exists():
        return {'updatedAt': at, 'method': METHOD_TEXT, 'records': []}
    football = {(r.identity, r.stage, r.issuedAt): r for r in football_statistics().records}
    racing = {(r.raceId, r.issuedAt): r for r in racing_statistics().records}
    result = []
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        for published, raw in db.execute('SELECT published_at,candidate FROM selections ORDER BY published_at DESC'):
            c = Candidate.model_validate_json(raw)
            receipt = football.get((c.identity, c.stage, c.issuedAt)) if c.domain == 'football' else racing.get((c.event, c.issuedAt))
            current = receipt.model_dump(mode='json') if receipt else {**c.receipt, 'status': 'excluded', 'reason': '暂时无法核对原推荐版本，未计成绩'}
            result.append({**c.model_dump(mode='json'), 'publishedAt': published, 'methodVersion': METHOD, 'receipt': current})
    return {'updatedAt': at, 'method': METHOD_TEXT, 'records': result}
