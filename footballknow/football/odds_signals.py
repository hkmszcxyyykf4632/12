"""Versioned, pre-match odds comparisons and out-of-sample signal settlement."""
import json
import math
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from .files import STATE, PUBLIC
from .odds_reference import policy
from .motivation import dt, digest
from .research_scope import SUPPORTED_COMPETITIONS

VERSION = 'fengyi-odds-change-v1'
KEYS = {'asian-handicap': 'HA', '90-minute-1x2': 'HDA', 'total-goals': 'OU'}
LABELS = {'asian-handicap': '亚洲让球', '90-minute-1x2': '胜平负', 'total-goals': '大小球'}


def read(path):
    try:
        return json.loads(path.read_text('utf-8'))
    except (OSError, ValueError):
        return {}


def identity(row):
    return digest([str(row['id']), dt(row['kickoff']).isoformat(),
                   *[str(row['teams'][s]['id']) for s in ('home', 'away')]])


@contextmanager
def connect():
    STATE.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(STATE / 'odds-observations.sqlite3', timeout=15)
    db.row_factory = sqlite3.Row
    db.executescript('''CREATE TABLE IF NOT EXISTS events
        (identity TEXT PRIMARY KEY, kickoff TEXT NOT NULL, content TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS observations
        (id INTEGER PRIMARY KEY, identity TEXT NOT NULL, series TEXT NOT NULL,
         at TEXT NOT NULL, signature TEXT NOT NULL, content TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS odds_event_series ON observations(identity,series,id);''')
    try:
        with db:
            yield db
    finally:
        db.close()


def valid_quote(q, at, cutoff=None):
    keys = KEYS.get(q.get('market'))
    stamp = dt(q.get('fetchedAt'))
    line, prices = q.get('line'), q.get('prices', {})
    return bool(keys and q.get('provider') and q.get('source') and stamp and stamp <= at
                and (cutoff is None or stamp < cutoff) and not q.get('inPlay')
                and q.get('scope', '90-minute') == '90-minute'
                and q.get('kind', 'bookmaker') == 'bookmaker'
                and all(type(prices.get(k)) in (int, float) and math.isfinite(prices[k])
                        and 1 < prices[k] <= 10000 for k in keys)
                and (q['market'] == '90-minute-1x2' or
                     type(line) in (int, float) and math.isfinite(line) and abs(line) <= 10
                     and abs(line * 4 - round(line * 4)) < 1e-8
                     and (q['market'] != 'total-goals' or line >= 0)))


def series(q):
    return (q['provider'], q['market'], q.get('via', ''))


def observe(rows, at=None):
    at = at or datetime.now(timezone.utc)
    with connect() as db:
        for row in rows:
            if str(row.get('competitionId')) not in SUPPORTED_COMPETITIONS or not dt(row.get('kickoff')):
                continue
            key, kickoff = identity(row), dt(row['kickoff'])
            saved = {k: row.get(k) for k in ('id', 'competitionId', 'league', 'kickoff', 'neutral', 'state',
                     'started', 'finished', 'scoreScope', 'teams', 'quotes', 'source', 'updatedAt')}
            db.execute('INSERT OR REPLACE INTO events VALUES (?,?,?)',
                       (key, kickoff.isoformat(), json.dumps(saved, ensure_ascii=False)))
            for q in row.get('quotes', []):
                if q.get('phase') not in ('opening', 'latest') or not valid_quote(q, at, kickoff):
                    continue
                group = json.dumps([*series(q), q['phase']])
                signature = digest([q.get('line'), q['prices']])
                last = db.execute('SELECT at,signature FROM observations WHERE identity=? AND series=? ORDER BY id DESC LIMIT 1',
                                  (key, group)).fetchone()
                if last and (q['phase'] == 'opening' or last['signature'] == signature or dt(q['fetchedAt']) <= dt(last['at'])):
                    continue
                db.execute('INSERT INTO observations(identity,series,at,signature,content) VALUES (?,?,?,?,?)',
                           (key, group, q['fetchedAt'], signature, json.dumps(q, ensure_ascii=False)))


def compare(before, after, basis, previous=None):
    if series(before) != series(after):
        return None
    keys = KEYS[after['market']]
    line_change = (after['line'] - before['line']) if after.get('line') is not None else 0
    raw_changes = {k: round(after['prices'][k] - before['prices'][k], 6) for k in keys}
    if not line_change and not any(abs(x) > 1e-6 for x in raw_changes.values()):
        return None
    fair = lambda q: {k: (1 / q['prices'][k]) / sum(1 / q['prices'][j] for j in keys) for k in keys}
    a, b = fair(before), fair(after)
    deltas = {k: round((b[k] - a[k]) * 100, 6) for k in keys}
    if line_change:
        side = ('H' if line_change < 0 else 'A') if after['market'] == 'asian-handicap' else ('O' if line_change > 0 else 'U')
        kind = 'line'
    else:
        side = max(keys, key=lambda k: deltas[k])
        if deltas[side] <= .0001:
            side = None
        kind = 'price'
    return {'basis': basis, 'kind': kind, 'market': after['market'], 'provider': after['provider'],
            'via': after.get('via', ''), 'side': side, 'lineChange': round(line_change, 4),
            'priceChanges': raw_changes, 'weightChangesPP': deltas if not line_change else None,
            'before': before, 'after': after, 'previousMatch': previous,
            'timeMeaning': '采集时间；来源未提供报价产生时间，不能据此确定变盘与消息发布的先后。'}


def historical_quotes(row, research, at):
    """Use already collected summaries, never invent a historical closing quote."""
    found = []
    for side in ('home', 'away'):
        team = research.get('teams', {}).get(side, {})
        for item in team.get('comparisons', {}).values():
            match = item.get('match', {})
            ident = str(match.get('id') or '')
            if not ident.isdigit():
                continue
            cached = read(STATE / 'match-summaries' / (ident + '.json'))
            raw, fetched = cached.get('raw', {}), dt(cached.get('updatedAt'))
            games = raw.get('header', {}).get('competitions') or []
            if not fetched or fetched > at or not games:
                continue
            if str(raw.get('header', {}).get('league', {}).get('id')) != str(row.get('competitionId')):
                continue
            game = games[0]
            kickoff = dt(game.get('date'))
            if not kickoff or kickoff >= dt(row['kickoff']) or not game.get('status', {}).get('type', {}).get('completed'):
                continue
            teams = {c.get('homeAway'): {'id': str(c.get('team', {}).get('id')), 'label': c.get('team', {}).get('displayName', '')}
                     for c in game.get('competitors', [])}
            if set(teams) != {'home', 'away'}:
                continue
            from .market_odds import espn_markets
            quotes = espn_markets(raw, ident, cached['updatedAt'])
            found.append({'id': ident, 'kickoff': kickoff.isoformat(), 'teams': teams, 'finished': True,
                          'competitionId': row.get('competitionId'), 'neutral': game.get('neutralSite', False),
                          'quotes': [q for q in quotes if q.get('phase') == 'closing'], 'historicalClosing': True})
    return found


def analyse(row, at, research=None):
    kickoff = dt(row['kickoff'])
    latest = {}
    for q in row.get('quotes', []):
        if (q.get('phase') == 'latest' and valid_quote(q, at, kickoff)
                and at - dt(q['fetchedAt']) <= timedelta(minutes=15)):
            key = series(q)
            if key not in latest or dt(q['fetchedAt']) > dt(latest[key]['fetchedAt']):
                latest[key] = q
    selected, reference = policy(list(latest.values()))
    latest = {series(q): q for q in selected}
    with connect() as db:
        history = [json.loads(r['content']) for r in db.execute('SELECT content FROM observations WHERE identity=? ORDER BY id', (identity(row),))]
        previous = [json.loads(r['content']) for r in db.execute('SELECT content FROM events WHERE kickoff<? AND kickoff>=? ORDER BY kickoff DESC',
                    (kickoff.isoformat(), (kickoff - timedelta(days=730)).isoformat()))]
    previous += historical_quotes(row, research or {}, at)
    changes, adjacent = [], []
    for key, current in sorted(latest.items()):
        earlier = [q for q in [*history, *row.get('quotes', [])] if valid_quote(q, at, kickoff) and series(q) == key
                   and q.get('phase') in ('opening', 'latest')]
        opening = sorted([q for q in earlier if q['phase'] == 'opening'], key=lambda q: dt(q['fetchedAt']))
        samples = sorted([q for q in earlier if q['phase'] == 'latest' and dt(q['fetchedAt']) < dt(current['fetchedAt'])], key=lambda q: dt(q['fetchedAt']))
        first = opening[0] if opening else samples[0] if samples else None
        if first:
            change = compare(first, current, 'opening' if opening else 'first-observed')
            if change:
                changes.append(change)
        candidates = sorted(previous, key=lambda p: p['kickoff'], reverse=True)
        for p in candidates:
            if (not p.get('finished') or str(p.get('competitionId')) != str(row.get('competitionId'))
                    or bool(p.get('neutral')) != bool(row.get('neutral'))
                    or any(str(p['teams'][s]['id']) != str(row['teams'][s]['id']) for s in ('home', 'away'))):
                continue
            old = [q for q in p.get('quotes', []) if series(q) == key
                   and q.get('phase') in ('latest', 'closing')
                   and valid_quote(q, at, None if p.get('historicalClosing') else dt(p['kickoff']))]
            if old:
                q = max(old, key=lambda q: dt(q['fetchedAt']))
                reference = {k: p.get(k) for k in ('id', 'kickoff', 'teams', 'neutral')}
                change = compare(q, current, 'same-opponent-same-venue', reference)
                if change:
                    changes.append(change)
                break
    for side in ('home', 'away'):
        old = next((p for p in sorted(previous, key=lambda p: p['kickoff'], reverse=True)
                    if p.get('finished') and any(str(t['id']) == str(row['teams'][side]['id']) for t in p['teams'].values())), None)
        if old:
            own = next(s for s in ('home', 'away') if str(old['teams'][s]['id']) == str(row['teams'][side]['id']))
            qs = [q for q in old.get('quotes', []) if q.get('market') == 'asian-handicap' and q.get('phase') in ('latest', 'closing')
                  and valid_quote(q, at, None if old.get('historicalClosing') else dt(old['kickoff']))]
            if qs:
                q = max(qs, key=lambda q: dt(q['fetchedAt']))
                adjacent.append({'team': row['teams'][side].get('label'), 'previousDate': old['kickoff'],
                    'previousOpponent': old['teams']['away' if own == 'home' else 'home'].get('label'),
                    'previousHomeAway': own, 'teamLine': q['line'] * (1 if own == 'home' else -1),
                    'quote': q, 'note': '相邻比赛仅作背景；对手或主客场不同，不单独触发预测。'})
    rank = {'asian-handicap': 0, '90-minute-1x2': 1, 'total-goals': 2}
    changes.sort(key=lambda c: (rank[c['market']], 0 if c['basis'] != 'same-opponent-same-venue' else 1,
                               -abs(c['lineChange']), -max((c['weightChangesPP'] or {'x': 0}).values()), c['provider'], c['via']))
    primary = next((c for c in changes if c['side']), None)
    return {'version': VERSION, 'eligible': bool(primary), 'primary': primary, 'changes': changes,
            'adjacentMatches': adjacent, 'checkedAt': at.isoformat(), 'referencePolicy': reference,
            'reason': '已发现可比的赛前变盘' if primary else
                      '只有价格整体调整，尚无明确方向，不作预测' if changes else
                      '没有可核对的赔率变化，不作预测；继续等待同场或同对手同主客场记录。'}


def profit(score, q, side):
    if q['market'] == '90-minute-1x2':
        result = 'H' if score[0] > score[1] else 'A' if score[0] < score[1] else 'D'
        return q['prices'][side] - 1 if result == side else -1
    line = q['line']
    legs = [math.floor(line * 2) / 2, math.ceil(line * 2) / 2]
    margins = [(score[0] - score[1] + v) * (1 if side == 'H' else -1) for v in legs] if q['market'] == 'asian-handicap' else [(sum(score) - v) * (1 if side == 'O' else -1) for v in legs]
    return sum(q['prices'][side] - 1 if v > 0 else -1 if v < 0 else 0 for v in margins) / 2


def reverse_profit(score, q, side):
    others = [k for k in KEYS[q['market']] if k != side]
    weights = {k: 1 / q['prices'][k] for k in others}
    return sum(profit(score, q, k) * weights[k] / sum(weights.values()) for k in others)


def statistics():
    from .football_forecasts import connect as forecast_db, resolved_result
    with connect() as db:
        events = {r['identity']: json.loads(r['content']) for r in db.execute('SELECT * FROM events')}
    # Fresh daily results take precedence over the long-term archive.
    events.update({identity(r): r for r in read(PUBLIC / 'daily-football.json').get('matches', []) if dt(r.get('kickoff'))})
    with forecast_db() as db:
        saved = db.execute('SELECT * FROM forecasts ORDER BY issued_at').fetchall()
    records, selected = [], {}
    for r in saved:
        content, snapshot = json.loads(r['content']), json.loads(r['snapshot'])
        if content.get('model') != VERSION or not content.get('oddsSignal'):
            continue
        event = snapshot['match']
        key = identity(event)
        # Use the first issued signal per event, never pick the better stage after results.
        selected.setdefault(key, (content, event))
    catalogues = {}
    for key, (report, frozen) in selected.items():
        row = resolved_result(events.get(key, frozen), catalogues)
        c = report['oddsSignal']
        score = [row['teams'][s].get('goals') for s in ('home', 'away')]
        settled = (row.get('finished') is True and all(type(n) is int and n >= 0 for n in score)
                   and row.get('scoreScope') == '90分钟含补时')
        follow = profit(score, c['after'], c['side']) if settled else None
        opposite = reverse_profit(score, c['after'], c['side']) if settled else None
        opening_return = profit(score, c['before'], c['side']) if settled and c['basis'] != 'same-opponent-same-venue' else None
        records.append({'eventId': row['id'], 'kickoff': row['kickoff'], 'competitionId': str(row['competitionId']),
            'teams': row['teams'], 'issuedAt': report['issuedAt'], 'signal': c, 'scorePrediction': report['score'],
            'status': 'settled' if settled else 'pending', 'score': score if settled else None,
            'exactScore': score in (report.get('scoreCandidates') or [report['score']]) if settled else None,
            'followNet': round(100 * follow, 2) if settled else None,
            'reverseNet': round(100 * opposite, 2) if settled else None,
            'earlierPriceNet': round(100 * opening_return, 2) if opening_return is not None else None})
    def total(rows):
        done = [r for r in rows if r['status'] == 'settled']
        count = len(done)
        wins = sum(r['followNet'] > 0 for r in done)
        net = round(sum(r['followNet'] for r in done), 2)
        return {'predictions': len(rows), 'settled': count, 'wins': wins,
                'losses': sum(r['followNet'] < 0 for r in done), 'pushes': sum(r['followNet'] == 0 for r in done),
                'exactScores': sum(r['exactScore'] for r in done), 'stake': 100 * count, 'net': net,
                'roi': round(net / count, 2) if count else None,
                'reverseNet': round(sum(r['reverseNet'] for r in done), 2)}
    return {'version': VERSION, 'updatedAt': datetime.now(timezone.utc).isoformat(), 'total': total(records),
            'competitions': {k: total([r for r in records if r['competitionId'] == k]) for k in SUPPORTED_COMPETITIONS},
            'groups': [{'basis': basis, 'market': market, **total([r for r in records if r['signal']['basis'] == basis and r['signal']['market'] == market])}
                       for basis in ('opening', 'first-observed', 'same-opponent-same-venue') for market in KEYS],
            'records': sorted(records, key=lambda r: r['kickoff'], reverse=True),
            'method': '固定第一份赛前变盘预测，每场一次，每方向模拟100；赢半/输半按半注结算，走盘不算命中。反向胜平负按其余两项等派回分配100。早期价格仅作事后价格对照，不算当时已推荐。样本不证明因果或未来收益；不同公司和历史对赛不混作同场变盘。'}
