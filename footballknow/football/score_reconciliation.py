"""Reconcile scores only after competition, kickoff and both opponents agree."""
from datetime import datetime


def stamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed.timestamp() if parsed.tzinfo else 0
    except (ValueError, TypeError, OverflowError):
        return 0


def confirmed(row):
    return bool(row.get('finished') and not row.get('provisional')
                and str(row.get('scoreScope', '')).startswith('90')
                and all(type(row.get(k)) is int and 0 <= row[k] <= 99 for k in ('homeGoals', 'awayGoals')))


def prefer_incoming(current, incoming):
    if confirmed(current) != confirmed(incoming):
        return confirmed(incoming)
    if current.get('finished') and not incoming.get('finished'):
        return False
    if current.get('started') and not incoming.get('started') and incoming.get('state') not in {'postponed', 'cancelled', 'abandoned'}:
        return False
    return stamp(incoming.get('scoreUpdatedAt') or incoming.get('updatedAt')) >= stamp(current.get('scoreUpdatedAt') or current.get('updatedAt'))


def same_fixture(match, row, catalogue, league):
    if row.get('league') != league or match['competition'] != catalogue.get('competition', '英超'):
        return False
    if match['season'] != catalogue['season'] or row.get('season') and str(row['season'])[:4] != match['season'][:4]:
        return False
    if not stamp(match.get('kickoff')) or stamp(match['kickoff']) != stamp(row.get('kickoff')):
        return False
    if match['id'].startswith('espn:') and match['id'] != 'espn:' + str(row.get('id')):
        return False
    for side in ('home', 'away'):
        team = next((t for t in catalogue.get('teams', []) if t['name'] == match[side]), {})
        other = row.get('teams', {}).get(side, {})
        if team.get('espnId') and other.get('id'):
            if str(team['espnId']) != str(other['id']):
                return False
        elif not (match[side] in (other.get('name'), other.get('originalName')) or team.get('cn') and team['cn'] == other.get('label')):
            return False
    return True


def reconcile(matches, catalogue, daily, league, updated_at=None):
    result = []
    for match in matches:
        candidates = [r for r in daily.get('matches', []) if same_fixture(match, r, catalogue, league)]
        row = dict(match)
        if len(candidates) == 1:
            incoming = candidates[0]
            h, a = (incoming.get('teams', {}).get(s, {}).get('goals') for s in ('home', 'away'))
            score = {k: incoming.get(k) for k in ('started', 'finished', 'scoreScope', 'state', 'status', 'clock')}
            score.update(homeGoals=h, awayGoals=a, provisional=False, updatedAt=incoming.get('updatedAt'),
                         scoreUpdatedAt=incoming.get('updatedAt'), scoreSource=incoming.get('source'))
            score['result'] = ('D' if h == a else 'H' if h > a else 'A') if score['finished'] and type(h) is int and type(a) is int else None
            row['dailyId'] = incoming['id']
            if (not score['finished'] or confirmed(score)) and prefer_incoming({**row, 'updatedAt': row.get('updatedAt') or updated_at}, score):
                row.update(score)
        result.append(row)
    return result
