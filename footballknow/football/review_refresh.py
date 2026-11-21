"""Bounded review work; every successful evidence revision becomes visible immediately."""
import hashlib
import json
from datetime import datetime, timedelta, timezone

from .ai import settings
from .files import PUBLIC, STATE, publish
from .match_research import load
from .sync_control import read_control


def ready(review):
    return review and review.get('analysisStatus') in {'ready', 'limited'}


def candidates(at):
    from .football_forecasts import connect, current_row, review, identity
    from .reviews import football_forecast_review, football_review
    from .racing_analysis import connect as racing_connect, public_status, generate
    from .racing import get_race
    with connect() as db:
        saved = [dict(r) for r in db.execute('SELECT identity,event_id,content FROM forecasts ORDER BY issued_at DESC LIMIT 100')]
    for item in saved:
        try:
            row = current_row(item['event_id'])
        except LookupError:
            continue
        if item['identity'] != identity(row):
            continue
        if not row.get('finished') or str(row.get('kickoff', ''))[:10] < (at - timedelta(days=7)).date().isoformat():
            continue
        original = json.loads(item['content'])
        result = review(original, row)
        audit = result.get('analysis')
        if audit and not ready(audit):
            yield audit, lambda row=row, original=original: football_forecast_review(row, original, True)
    # Editorial fact supplements can be published without inventing an old prediction.
    for case in load(PUBLIC / 'review-evidence' / 'football.json').get('cases', []):
        fixture = case.get('identity', {})
        try:
            result = football_review(fixture['id'], fixture['league'])
        except (LookupError, KeyError):
            continue
        audit = result.get('review')
        if audit and not ready(audit):
            yield audit, lambda f=fixture: football_review(f['id'], f['league'], True)
    with racing_connect() as db:
        ids = [r['race_id'] for r in db.execute("SELECT race_id FROM reports WHERE phase='pre' ORDER BY issued_at DESC LIMIT 30")]
    for ident in ids:
        race = get_race(ident)
        if race.get('status') != 'finished' or str(race.get('date', '')) < (at - timedelta(days=7)).date().isoformat():
            continue
        audit = public_status(ident)['reports'].get('post')
        if audit and not ready(audit):
            yield audit, lambda ident=ident: generate(ident, 'post')


def refresh():
    if not read_control()['enabled']:
        return {'paused': True, 'generated': 0}
    if not settings().apiKey.get_secret_value():
        return {'generated': 0, 'message': '分析服务尚未配置；已核实事实仍可查看。'}
    at = datetime.now(timezone.utc)
    path = STATE / 'evidence-review-attempts.json'
    attempts = load(path)
    for audit, action in candidates(at):
        key = hashlib.sha256(audit['revision'].encode()).hexdigest()
        previous = attempts.get(key)
        if previous and at - datetime.fromisoformat(previous) < timedelta(minutes=30):
            continue
        attempts[key] = at.isoformat()
        publish(path, dict(list(attempts.items())[-500:]))
        action()
        return {'generated': 1, 'revision': audit['revision']}
    return {'generated': 0}
