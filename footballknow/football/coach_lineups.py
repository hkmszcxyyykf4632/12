"""Compact, attributed starting elevens for coach-tenure comparisons."""
import json
import threading
import time
from .files import PUBLIC
from .leagues import league_path
from .history import CLUB_ALIASES

_cache = {}
_lock = threading.RLock()


def _read(path):
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return {}


def _snapshot(league):
    folder = league_path(PUBLIC, league)
    key = str(folder)
    with _lock:
        previous = _cache.get(key)
        if previous and time.monotonic() - previous[0] < 30:
            return previous[2]
        files = [folder / 'data.json', folder / 'names.json', *sorted((folder / 'match-details').glob('*.json'))]
        signature = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in files if p.is_file())
        if previous and previous[1] == signature:
            value = previous[2]
        else:
            data, names = _read(files[0]), _read(files[1]).get('names', {})
            rows = []
            for path in files[2:]:
                detail = _read(path)
                if detail.get('league') != league or not detail.get('date') or not detail.get('matchId'):
                    continue
                for side, lineup in detail.get('lineups', {}).items():
                    if side not in ('home', 'away') or not lineup.get('confirmed') or lineup.get('name') != detail.get(side):
                        continue
                    starters = [p for p in lineup.get('players', []) if p.get('starter') is True]
                    ids = [str(p.get('espnId') or '') for p in starters]
                    if len(starters) != 11 or len(set(ids)) != 11 or not all(ids):
                        continue
                    rows.append({'league': league, 'matchId': detail['matchId'], 'eventId': detail.get('eventId'),
                                 'date': detail['date'], 'home': detail.get('home'), 'away': detail.get('away'),
                                 'team': lineup['name'], 'formation': lineup.get('formation') or '',
                                 'source': detail.get('source'), 'updatedAt': detail.get('updatedAt'),
                                 'starters': [{'id': str(p['espnId']), 'code': p.get('playerCode'),
                                               'name': names.get(str(p.get('playerCode')), {}).get('mandarin') or p.get('name'),
                                               'english': p.get('name'), 'position': p.get('position') or ''} for p in starters]})
            value = (data.get('teams', []), rows)
        _cache[key] = (time.monotonic(), signature, value)
        return value


def coach_lineups(league, team_id):
    teams, rows = _snapshot(league)
    team = next((t for t in teams if str(t['id']) == str(team_id)), None)
    if not team:
        raise LookupError('球队不存在。')
    canonical = lambda name: CLUB_ALIASES.get(name, name)
    selected = [r for r in rows if canonical(r['team']) == canonical(team['name'])]
    return {'league': league, 'teamId': str(team_id), 'team': team['name'], 'matches': selected,
            'scope': '采用本站已收录的正式首发；缺少相邻场次名单时不推断人员变化。'}
