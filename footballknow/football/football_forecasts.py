"""Timed, immutable football forecasts with pre-kickoff source receipts."""
import json
import math
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .files import PUBLIC, STATE
from .match_research import load, research_row
from .motivation import digest, dt
from .sync_control import read_control
from .research_scope import SUPPORTED_COMPETITIONS

COMPETITIONS = SUPPORTED_COMPETITIONS
HK = timezone(timedelta(hours=8))
FINAL_WINDOW = timedelta(minutes=120)
INITIAL_WINDOW = timedelta(hours=96)
from . import odds_signals
from .odds_forecast import build as build_prediction



def now():
    return datetime.now(timezone.utc)


@contextmanager
def connect():
    STATE.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(STATE / 'football-forecasts.sqlite3', timeout=15)
    db.row_factory = sqlite3.Row
    db.executescript('''CREATE TABLE IF NOT EXISTS forecasts (
        identity TEXT NOT NULL, stage TEXT NOT NULL, event_id TEXT NOT NULL,
        issued_at TEXT NOT NULL, content TEXT NOT NULL, snapshot TEXT NOT NULL,
        PRIMARY KEY(identity,stage));
        CREATE TABLE IF NOT EXISTS attempts (
        identity TEXT NOT NULL, stage TEXT NOT NULL, retry_at TEXT NOT NULL,
        failures INTEGER NOT NULL DEFAULT 0, message TEXT NOT NULL,
        PRIMARY KEY(identity,stage));
        CREATE TABLE IF NOT EXISTS forecast_amendments (
        id TEXT PRIMARY KEY, identity TEXT NOT NULL, stage TEXT NOT NULL,
        issued_at TEXT NOT NULL, content TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS forecast_amendments_identity ON forecast_amendments(identity,stage);
        CREATE TRIGGER IF NOT EXISTS forecast_amendments_no_update
        BEFORE UPDATE ON forecast_amendments BEGIN SELECT RAISE(ABORT, 'amendments are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS forecast_amendments_no_delete
        BEFORE DELETE ON forecast_amendments BEGIN SELECT RAISE(ABORT, 'amendments are append-only'); END;''')
    try:
        with db:
            yield db
    finally:
        db.close()


def identity(row):
    return digest({'id': row['id'], 'kickoff': dt(row['kickoff']).isoformat(),
                   'teams': {s: str(row['teams'][s]['id']) for s in ['home', 'away']}})


def supported(row):
    return str(row.get('competitionId')) in COMPETITIONS and bool(dt(row.get('kickoff')))


def pregame(row, at):
    return (supported(row) and row.get('state') == 'scheduled' and not row.get('started')
            and not row.get('finished') and at < dt(row['kickoff']))


def fresh(value, at, minutes):
    stamp = dt(value)
    return bool(stamp and timedelta(0) <= at - stamp <= timedelta(minutes=minutes))


def confirmed(research, row, at):
    if (research.get('eventId') != row['id'] or dt(research.get('kickoff')) != dt(row['kickoff'])
            or research.get('message') or not fresh(research.get('pregame', {}).get('capturedAt'), at, 10)):
        return False
    for side in ['home', 'away']:
        team = research.get('teams', {}).get(side, {})
        lineup = team.get('lineup', {})
        ids = [p.get('id') for p in lineup.get('players', [])]
        if (str(team.get('teamId')) != str(row['teams'][side]['id']) or lineup.get('confirmed') is not True
                or len(ids) != 11 or len(set(ids)) != 11 or not all(ids)):
            return False
    return True


def quote_for(row, at):
    rows = []
    for q in row.get('quotes', []):
        line, prices = q.get('line'), q.get('prices', {})
        if (q.get('market') != 'asian-handicap' or q.get('phase') != 'latest'
                or q.get('inPlay') or not fresh(q.get('fetchedAt'), at, 15)
                or not dt(q.get('fetchedAt')) < dt(row['kickoff']) or not q.get('source')
                or type(line) not in (int, float) or not math.isfinite(line) or abs(line) > 10
                or abs(line * 4 - round(line * 4)) > 1e-8
                or any(type(prices.get(s)) not in (int, float) or not math.isfinite(prices[s]) or prices[s] <= 1 for s in ['H', 'A'])):
            continue
        rows.append(q)
    rows.sort(key=lambda q: (q['phase'] == 'latest', dt(q['fetchedAt'])), reverse=True)
    return rows[0] if rows else None


def settlement(goals, line, side):
    diff = goals[0] - goals[1]
    lines = [math.floor(line * 2) / 2, math.ceil(line * 2) / 2]
    results = [((diff + x) > 0) - ((diff + x) < 0) for x in lines]
    value = sum(results) / 2 * (1 if side == 'H' else -1)
    return {1: '赢盘', .5: '赢半', 0: '走盘', -.5: '输半', -1: '输盘'}[value]


def baseline(research, cutoff):
    samples, rates = {}, {}
    for side in ['home', 'away']:
        rows = [r for r in research.get('teams', {}).get(side, {}).get('form', {}).get('matches', [])
                if dt(r.get('date')) and dt(r['date']) < cutoff
                and all(type(r.get(k)) is int and 0 <= r[k] <= 20 for k in ['goalsFor', 'goalsAgainst'])]
        rows = sorted(rows, key=lambda r: dt(r['date']), reverse=True)[:10]
        samples[side] = len(rows)
        if len(rows) < 3:
            return {'available': False, 'samples': samples, 'reason': '双方均需至少三场可核对往绩'}
        weights = [(.85 ** i) * (1.2 if r.get('homeAway') == side else 1) for i, r in enumerate(rows)]
        rates[side] = {k: sum(r[k] * w for r, w in zip(rows, weights)) / sum(weights)
                       for k in ['goalsFor', 'goalsAgainst']}
    home = max(.2, min(4.5, (rates['home']['goalsFor'] + rates['away']['goalsAgainst']) / 2))
    away = max(.2, min(4.5, (rates['away']['goalsFor'] + rates['home']['goalsAgainst']) / 2))
    grid = [{'score': [h, a], 'weight': math.exp(-home-away) * home**h * away**a / math.factorial(h) / math.factorial(a)}
            for h in range(13) for a in range(13)]
    grid.sort(key=lambda x: x['weight'], reverse=True)
    return {'available': True, 'samples': samples, 'expectedGoals': [round(home, 2), round(away, 2)],
            'leadingScores': [r['score'] for r in grid[:5]],
            'method': '最近10场按0.85逐场递减，同主客场权重乘1.2；本队进球与对手失球均值取平均，限0.2至4.5；独立泊松比分。未作概率校准。'}


class Detail(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=40)
    text: str = Field(min_length=1, max_length=600)


class Content(BaseModel):
    model_config = ConfigDict(extra='forbid')
    score: list[int] = Field(min_length=2, max_length=2)
    scoreCandidates: list[list[int]] = Field(default_factory=list, max_length=2)
    asianSide: Literal['H', 'A', 'pass']
    summary: list[str] = Field(min_length=2, max_length=2)
    details: list[Detail] = Field(min_length=1, max_length=5)


def baseline_explanation(report):
    scores = report.get('baseline', {}).get('leadingScores', [])
    score = scores[0] if scores else None
    chosen = report.get('score')
    if not (isinstance(score, list) and len(score) == 2 and isinstance(chosen, list) and len(chosen) == 2):
        return None
    text = f'封存统计基线首选 {score[0]}:{score[1]}；本版实际主选 {chosen[0]}:{chosen[1]}。'
    text += '两者不同，主选属于模型调整，不能称为沿用统计首选。' if score != chosen else '本版比分与统计首选一致。'
    return {'baselineScore': score, 'selectedScore': chosen, 'differsFromBaseline': score != chosen,
            'source': 'stored-report.baseline.leadingScores[0]', 'text': text}


def validate(value, quote, stats=None, previous=None):
    if any(type(n) is not int or not 0 <= n <= 12 for n in value.get('score', [])):
        raise ValueError('比分格式未通过检查')
    report = Content.model_validate(value)
    if report.scoreCandidates and (report.scoreCandidates[0] != report.score or len({tuple(v) for v in report.scoreCandidates}) != len(report.scoreCandidates) or any(len(v) != 2 or any(type(n) is not int or not 0 <= n <= 12 for n in v) for v in report.scoreCandidates)):
        raise ValueError('候选比分必须唯一且首项等于主选比分')
    if any(not p.strip() or len(p) > 150 for p in report.summary):
        raise ValueError('预测摘要格式未通过检查')
    if quote is None and report.asianSide != 'pass':
        raise ValueError('未取得盘口，不能生成让球盘方向')
    prose = '\n'.join([*report.summary, *(part.text for part in report.details)])
    checks = [(r'(?:统计(?:基线)?(?:的)?首选(?:比分)?|基线(?:的)?首选(?:比分)?)',
               ((stats or {}).get('leadingScores') or [None])[0]),
              (r'初版(?:的)?(?:预测比分|主选比分|首选比分|比分|主选|首选)', (previous or {}).get('score'))]
    for subject, expected in checks:
        for match in re.finditer(subject + r'[^。；，\n\d]{0,12}(\d{1,2})\s*[:：比-]\s*(\d{1,2})', prose):
            if expected is not None and [int(match[1]), int(match[2])] != expected:
                raise ValueError('预测文字误述封存统计首选或初版比分')
    return report.model_dump()


def reports_for(row, db):
    result = {}
    for r in db.execute('SELECT * FROM forecasts WHERE identity=?', (identity(row),)):
        result[r['stage']] = json.loads(r['content'])
    for r in db.execute('SELECT stage,content FROM forecast_amendments WHERE identity=? ORDER BY issued_at,id', (identity(row),)):
        if r['stage'] in result:
            result[r['stage']].setdefault('amendments', []).append(json.loads(r['content']))
    return result


def record_baseline_amendment(row, stage, reason):
    at = now()
    latest = current_row(row['id'])
    if stage not in {'initial', 'final'} or not pregame(latest, at) or identity(latest) != identity(row):
        raise ValueError('只能为身份一致且尚未开赛的封存预测追加更正')
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
        raise ValueError('更正原因须为1至500字')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        stored = db.execute('SELECT content,snapshot FROM forecasts WHERE identity=? AND stage=?', (identity(row), stage)).fetchone()
        if not stored:
            raise LookupError('尚无本阶段封存预测')
        report = json.loads(stored['content'])
        explanation = baseline_explanation(report)
        if not explanation:
            raise ValueError('封存统计基线缺失，不能推测更正内容')
        original_snapshot = json.loads(stored['snapshot'])
        previous_score = (original_snapshot.get('initialPrediction') or {}).get('score')
        facts = {}
        for side in ('home', 'away'):
            team = original_snapshot.get('research', {}).get('teams', {}).get(side, {})
            form, lineup, comparisons = team.get('form', {}), team.get('lineup', {}), team.get('comparisons', {})
            facts[side] = {'name': team.get('name') or original_snapshot.get('match', {}).get('teams', {}).get(side, {}).get('label'),
                           'formSummary': form.get('summary'), 'run': form.get('run'), 'outcome': form.get('outcome'),
                           'formation': lineup.get('formation'), 'lineupConfirmed': lineup.get('confirmed') is True,
                           'previousRetained': comparisons.get('previous', {}).get('difference', {}).get('retained'),
                           'headToHeadRetained': comparisons.get('headToHead', {}).get('difference', {}).get('retained'),
                           'source': f'stored-snapshot.research.teams.{side}'}
        text = explanation['text']
        if previous_score:
            text += f'本版生成时引用的初版实际预测为 {previous_score[0]}:{previous_score[1]}。'
        text += '本说明仅更正统计事实，不补造当时的调整依据；原预测比分、亚洲盘方向和快照保持封存。'
        amendment = {'kind': 'baseline-factual-correction', 'stage': stage, 'issuedAt': at.isoformat(),
                     'reason': reason.strip(), 'text': text, 'baselineExplanation': explanation,
                     'facts': facts,
                     'initialPredictionScore': previous_score, 'originalReportHash': digest(report),
                     'originalSnapshotHash': digest(original_snapshot)}
        amendment['id'] = digest(amendment)
        if not pregame(latest, now()):
            raise ValueError('已过开赛时间，未追加赛前更正')
        db.execute('INSERT OR IGNORE INTO forecast_amendments VALUES (?,?,?,?,?)',
                   (amendment['id'], identity(row), stage, amendment['issuedAt'], json.dumps(amendment, ensure_ascii=False)))
    return amendment


def review(report, row, *, detailed=True):
    if row.get('state') in {'postponed', 'cancelled', 'abandoned'}:
        return {'status': 'void', 'text': '延期、取消或中断，暂不计结果'}
    if not row.get('finished') or row.get('state') != 'finished':
        return {'status': 'pending'}
    score = [row['teams'][s].get('goals') for s in ['home', 'away']]
    if any(type(x) is not int or x < 0 for x in score) or str(row.get('scoreScope', '')).replace(' ', '') != '90分钟含补时':
        return {'status': 'pending', 'text': '等待可核对的90分钟赛果'}
    direction = lambda v: (v[0] > v[1]) - (v[0] < v[1])
    q = report.get('quote')
    ah = settlement(score, q['line'], report['asianSide']) if q and report['asianSide'] != 'pass' else '未选边'
    audit = None
    if detailed:
        from .reviews import football_forecast_review
        audit = football_forecast_review(row, report)
    return {'status': 'evaluated', 'score': score, 'exactScore': score in (report.get('scoreCandidates') or [report['score']]), 'analysis': audit,
            'resultHit': direction(score) == direction(report['score']), 'asianResult': ah,
            'text': f'完场{score[0]}:{score[1]}；比分' + ('命中' if score in (report.get('scoreCandidates') or [report['score']]) else '未命中') + f'；亚洲盘{ah}。',
            'source': row.get('source')}


def status(row, at=None, saved=None, tries=None, paused=None, *, detailed_review=True):
    at = at or now()
    if not supported(row):
        return {'supported': False}
    if saved is None:
        with connect() as db:
            saved = reports_for(row, db)
            tries = {r['stage']: dict(r) for r in db.execute('SELECT * FROM attempts WHERE identity=?', (identity(row),))}
    reports, attempts = saved, tries or {}
    paused = not read_control()['enabled'] if paused is None else paused
    stages = {}
    for stage in ['initial', 'final']:
        report = reports.get(stage)
        attempt = attempts.get(stage, {})
        message = ('同步已暂停，恢复后自动检查' if paused else
                   '已过开赛时间，未留下本阶段预测' if not pregame(row, at) else
                   attempt.get('message') or ('开赛前96小时自动生成' if stage == 'initial' else '开赛前120分钟开始准备并检查，双方正式首发确认后生成'))
        stages[stage] = {'report': {**report, 'baselineExplanation': baseline_explanation(report), 'amendments': report.get('amendments', []),
                                   'review': review(report, row, detailed=detailed_review)} if report else None,
                         'message': message, 'retryAt': attempt.get('retry_at')}
    return {'supported': True, 'eventId': row['id'], 'kickoff': row['kickoff'],
            'teams': {s: str(row['teams'][s]['id']) for s in ['home', 'away']},
            'initialAt': (dt(row['kickoff']) - INITIAL_WINDOW).isoformat(),
            'finalCheckAt': (dt(row['kickoff']) - FINAL_WINDOW).isoformat(),
            'paused': paused, 'stages': stages}


def current_row(ident):
    if not re.fullmatch(r'\d{1,16}', str(ident)):
        raise LookupError('赛事编号格式不正确')
    row = next((r for r in load(PUBLIC / 'daily-football.json').get('matches', []) if r.get('id') == ident), None)
    if not row:
        raise LookupError('每日赛事尚未收录本场比赛')
    return resolved_result(row)


def resolved_result(row, catalogues=None):
    """A validated league final result can advance an older daily scoreboard."""
    from .match_details import match_catalogue
    from .match_centre_research import same_fixture
    league = row.get('league') or {'700': 'epl', '720': 'bundesliga', '730': 'seriea', '740': 'laliga', '775': 'ucl'}.get(str(row.get('competitionId')))
    if league not in {'epl', 'bundesliga', 'seriea', 'laliga', 'ucl'}:
        return row
    if catalogues is None:
        _, matches = match_catalogue(league)
    else:
        if league not in catalogues:
            catalogues[league] = match_catalogue(league)[1]
        matches = catalogues[league]
    match = next((m for m in matches if same_fixture({**row, 'league': league}, m, league) and m.get('finished')), None)
    if not match or not all(type(match.get(s + 'Goals')) is int for s in ('home', 'away')):
        return row
    return {**row, 'finished': True, 'started': True, 'state': 'finished', 'scoreScope': match.get('scoreScope', row.get('scoreScope')),
            'teams': {s: {**row['teams'][s], 'goals': match[s + 'Goals']} for s in ('home', 'away')}}


def compact_status(value):
    result = {k: v for k, v in value.items() if k != 'stages'}
    result['stages'] = {}
    for name, stage in value.get('stages', {}).items():
        report = stage.get('report')
        short = {k: report.get(k) for k in ('score', 'scoreCandidates', 'asianSide', 'issuedAt')} if report else None
        if short is not None:
            short['quote'] = {'line': report['quote']['line']} if report.get('quote') else None
            short['review'] = {'status': (report.get('review') or {}).get('status')}
        result['stages'][name] = {**{k: v for k, v in stage.items() if k != 'report'}, 'report': short}
    return result


def read_index(compact=False):
    catalogues = {}
    rows = [resolved_result(r, catalogues) for r in load(PUBLIC / 'daily-football.json').get('matches', []) if supported(r)]
    keys = [identity(r) for r in rows]
    reports, attempts = {}, {}
    with connect() as db:
        for start in range(0, len(keys), 400):
            chunk = keys[start:start+400]
            placeholders = ','.join('?' for _ in chunk)
            for r in db.execute(f'SELECT identity,stage,content FROM forecasts WHERE identity IN ({placeholders})', chunk):
                reports.setdefault(r['identity'], {})[r['stage']] = json.loads(r['content'])
            for r in db.execute(f'SELECT * FROM attempts WHERE identity IN ({placeholders})', chunk):
                attempts.setdefault(r['identity'], {})[r['stage']] = dict(r)
            for r in db.execute(f'SELECT identity,stage,content FROM forecast_amendments WHERE identity IN ({placeholders}) ORDER BY issued_at,id', chunk):
                report = reports.get(r['identity'], {}).get(r['stage'])
                if report is not None:
                    report.setdefault('amendments', []).append(json.loads(r['content']))
    at, paused = now(), not read_control()['enabled']
    values = {r['id']: status(r, at, reports.get(identity(r), {}), attempts.get(identity(r), {}), paused,
                             detailed_review=not compact) for r in rows}
    return {'updatedAt': at.isoformat(), 'compact': compact,
            'matches': {key: compact_status(value) for key, value in values.items()} if compact else values}


def claim(row, stage, at):
    key = identity(row)
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if stage in reports_for(row, db):
            return False
        old = db.execute('SELECT * FROM attempts WHERE identity=? AND stage=?', (key, stage)).fetchone()
        if old and dt(old['retry_at']) > at:
            return False
        db.execute('INSERT OR REPLACE INTO attempts VALUES (?,?,?,?,?)',
                   (key, stage, (at + timedelta(minutes=10)).isoformat(), old['failures'] if old else 0, '正在核对资料并生成预测'))
    return True


def defer(row, stage, message, failed=False):
    with connect() as db:
        old = db.execute('SELECT failures FROM attempts WHERE identity=? AND stage=?', (identity(row), stage)).fetchone()
        count = (old['failures'] if old else 0) + int(failed)
        delay = min(1800, 120 * 2**min(count, 4)) if failed else 60
        if dt(row['kickoff']) - now() <= FINAL_WINDOW:
            delay = min(delay, 60)
        db.execute('INSERT OR REPLACE INTO attempts VALUES (?,?,?,?,?)',
                   (identity(row), stage, (now() + timedelta(seconds=delay)).isoformat(), count, message))


def generate(row, stage):
    at = now()
    if stage not in {'initial', 'final'} or not read_control()['enabled'] or not pregame(row, at) or not claim(row, stage, at):
        return False
    try:
        if not fresh(row.get('updatedAt'), at, 10):
            defer(row, stage, '等待赛程和盘口来源更新')
            return False
        odds_signals.observe([row], at)
        if not quote_for(row, at):
            defer(row, stage, '没有可核对的最新亚洲盘，暂不预测')
            return False
        research = research_row(row)
        valid = (research.get('eventId') == row['id'] and dt(research.get('kickoff')) == dt(row['kickoff'])
                 and all(str(research.get('teams', {}).get(s, {}).get('teamId')) == str(row['teams'][s]['id']) for s in ['home', 'away'])
                 and not research.get('message') and fresh(research.get('pregame', {}).get('capturedAt'), now(), 10))
        if not valid or stage == 'final' and not confirmed(research, row, now()):
            defer(row, stage, '等待双方正式首发及最新资料' if stage == 'final' else '等待双方赛前往绩资料更新')
            return False
        stats = baseline(research, min(now(), dt(row['kickoff'])))
        if not stats['available']:
            defer(row, stage, '双方可核对往绩不足，等待补充')
            return False
        signal = odds_signals.analyse(row, now(), research)
        primary = signal['primary']
        quote = primary['after'] if primary and primary['market'] == 'asian-handicap' else quote_for(row, now())
        if not signal['eligible'] or not quote:
            defer(row, stage, signal['reason'] if not signal['eligible'] else '等待最新亚洲盘')
            return False
        with connect() as db:
            previous = reports_for(row, db).get('initial')
        from .evidence_reviews import method_memory
        snapshot = {'stage': stage, 'capturedAt': now().isoformat(), 'match': row, 'research': research,
                    'reviewLessons': method_memory('football', row['kickoff']),
                    'reviewLessonInstructions': '这些是过去复盘提出的候选检查项。只核查本场适用的条件，不把一次赛果当成规律，不自动提高胜率或更改权重。',
                    'quote': quote, 'baseline': stats, 'initialPrediction': previous,
                    'oddsSignal': signal}
        value = build_prediction({**snapshot, 'at': now(), 'cutoff': dt(row['kickoff'])})
        value.pop('model', None)
        content = validate(value, quote, stats, previous)
        finished = now()
        latest = current_row(row['id'])
        if not read_control()['enabled'] or not pregame(latest, finished) or identity(latest) != identity(row):
            defer(row, stage, '生成期间赛事状态改变，未保存为赛前预测')
            return False
        if stage == 'final' and not confirmed(research, row, finished):
            defer(row, stage, '阵容资料已过时，重新核对后再生成')
            return False
        content.update({'issuedAt': finished.isoformat(), 'model': odds_signals.VERSION, 'oddsSignal': signal['primary'], 'stage': stage,
                        'quote': quote, 'snapshotHash': digest(snapshot), 'researchAt': research.get('pregame', {}).get('capturedAt'),
                        'lineupsConfirmed': confirmed(research, row, finished), 'baseline': stats})
        with connect() as db:
            db.execute('INSERT OR IGNORE INTO forecasts VALUES (?,?,?,?,?,?)',
                       (identity(row), stage, row['id'], finished.isoformat(), json.dumps(content, ensure_ascii=False), json.dumps(snapshot, ensure_ascii=False)))
            db.execute('DELETE FROM attempts WHERE identity=? AND stage=?', (identity(row), stage))
        return True
    except Exception:
        # Provider errors can contain credentials or response bodies; never publish them.
        defer(row, stage, '分析暂未完成，稍后自动重试', True)
        return False


def refresh(bootstrap_day=None):
    if not read_control()['enabled']:
        return {'paused': True, 'generated': 0}
    at = now()
    candidates = []
    for row in load(PUBLIC / 'daily-football.json').get('matches', []):
        if not pregame(row, at):
            continue
        left = dt(row['kickoff']) - at
        with connect() as db:
            saved = reports_for(row, db)
            attempts = {r['stage']: dict(r) for r in db.execute('SELECT * FROM attempts WHERE identity=?', (identity(row),))}
        for stage in ['final', 'initial']:
            if stage == 'final' and 'initial' not in saved and 'initial' not in attempts:
                continue
            due = left <= FINAL_WINDOW if stage == 'final' else (
                left <= INITIAL_WINDOW or bootstrap_day == dt(row['kickoff']).astimezone(HK).date().isoformat())
            attempt = attempts.get(stage)
            if due and stage not in saved and (not attempt or dt(attempt['retry_at']) <= at):
                last_retry = dt(attempt['retry_at']) if attempt else datetime.min.replace(tzinfo=timezone.utc)
                candidates.append((0 if stage == 'final' else 1, dt(row['kickoff']), row, stage, last_retry))
    candidates.sort(key=lambda c: (c[0], c[4], c[1]))
    # Rotate pending matches so one unpublished lineup cannot monopolize the queue.
    finals = [c for c in candidates if c[3] == 'final']
    initials = [c for c in candidates if c[3] == 'initial']
    selected = finals[:1] + initials[:1] if finals and initials else candidates[:2]
    count = sum(generate(row, stage) for _, _, row, stage, _ in selected)
    return {'checked': len(selected), 'generated': count, 'queued': max(0, len(candidates) - len(selected))}
