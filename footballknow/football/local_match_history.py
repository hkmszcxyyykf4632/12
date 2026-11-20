"""Use already collected club results when the remote team schedule is unavailable."""
from datetime import datetime, timezone
from .files import PUBLIC
from .leagues import LEAGUES, league_path
from .motivation import dt


def local_history(team_id, before, load):
    from .match_details import canonical
    rows = {}
    for league in LEAGUES:
        folder = league_path(PUBLIC, league)
        data, live, table = (load(folder / (name + '.json')) for name in ('data', 'live', 'standings'))
        clubs = [*data.get('teams', []), *table.get('entries', [])]
        ids = {canonical(t['name'], league): str(t['espnId']) for t in clubs if t.get('espnId')}
        own_names = {key for key, ident in ids.items() if ident == team_id}
        if not own_names:
            continue
        for match in [*data.get('matches', []), *live.get('matches', [])]:
            date = dt(match.get('kickoff'))
            date_only = date is None
            if date_only:
                try:
                    date = datetime.strptime(match.get('date', ''), '%Y-%m-%d').replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
                if date.date() >= before.date():
                    continue
            if not date or date >= before or not match.get('finished') or match.get('provisional'):
                continue
            side = next((s for s in ('home', 'away') if canonical(match.get(s, ''), league) in own_names), None)
            if not side:
                continue
            other = 'away' if side == 'home' else 'home'
            own, against = match.get(side + 'Goals'), match.get(other + 'Goals')
            if not all(type(v) is int and 0 <= v <= 99 for v in (own, against)):
                continue
            opponent_id = ids.get(canonical(match[other], league), '')
            key = (date.date().isoformat(), side, opponent_id or canonical(match[other], league))
            event_id = match['id'].removeprefix('espn:') if match['id'].startswith('espn:') else None
            previous = rows.get(key)
            if previous and previous.get('id') and not event_id:
                continue
            rows[key] = {'id': event_id, 'date': date.isoformat(), 'dateOnly': date_only, 'homeAway': side,
                         'opponentId': opponent_id, 'opponent': match[other], 'goalsFor': own, 'goalsAgainst': against,
                         'result': 'W' if own > against else 'L' if own < against else 'D',
                         'competition': match.get('competition'), 'scope': match.get('scoreScope'),
                         'source': match.get('source'), 'catalogueLeague': league, 'catalogueMatch': match}
    return sorted(rows.values(), key=lambda r: r['date'], reverse=True)
