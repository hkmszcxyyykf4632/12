"""Season facts derived from stored match summaries.

The leaders feed of the upstream source is refused from time to time; the lineups and
team statistics of each match are a second, independent route to the same totals. Anything
that cannot be verified against the final score is left out instead of guessed.
"""
from datetime import datetime, timezone
import re

GOALS = {'goal', 'penalty---scored', 'own-goal'}
TEAM_STATS = ['possessionPct', 'totalShots', 'shotsOnTarget', 'blockedShots', 'wonCorners', 'offsides', 'foulsCommitted',
              'totalPasses', 'accuratePasses', 'totalCrosses', 'accurateCrosses', 'totalLongBalls', 'accurateLongBalls',
              'totalTackles', 'effectiveTackles', 'interceptions', 'totalClearance', 'saves', 'yellowCards', 'redCards']


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clock_minute(clock):
    """Sortable minute for "45'+2'" style clocks; None when it cannot be read."""
    text = str(clock or '').replace("'", '').strip()
    if not re.fullmatch(r'\d+(?:\+\d+)?', text):
        return None
    parts = text.split('+')
    return sum(int(p) for p in parts) + (0.5 if len(parts) > 1 else 0) if parts else None


def score_timeline(match, detail):
    """Half-time score and who scored first, only when the listed goals add up to the final score."""
    goals = [e for e in detail.get('events', []) if e.get('type') in GOALS and e.get('side') in ('home', 'away')]
    tally = [sum(e['side'] == side for e in goals) for side in ('home', 'away')]
    if tally != [match.get('homeGoals'), match.get('awayGoals')]:
        return None
    if any(e.get('period') not in (1, 2, 3, 4) for e in goals):
        return None
    first = [sum(e['side'] == side and e.get('period') == 1 for e in goals) for side in ('home', 'away')]
    timed = [(clock_minute(e.get('clock')), e) for e in goals]
    opener = min((item for item in timed if item[0] is not None), key=lambda item: (item[1].get('period') or 9, item[0]), default=None)
    return {'halfTime': first, 'firstGoal': opener[1]['side'] if opener and all(t is not None for t, _ in timed) else None}


def outcome(match, side):
    home, away = match['homeGoals'], match['awayGoals']
    if home == away:
        return 'd'
    return 'w' if (home > away) == (side == 'home') else 'l'


def build_facts(league, catalogue, competition, pairs, target):
    """pairs: (catalogue match, stored detail) for finished matches with confirmed lineups."""
    matches, players, teams = {}, {}, {}
    for match, detail in pairs:
        if detail.get('status') != 'available' or not isinstance(match.get('homeGoals'), int) or not isinstance(match.get('awayGoals'), int):
            continue
        timeline = score_timeline(match, detail)
        entry = {'venue': detail.get('venue') or '', 'attendance': detail.get('attendance')}
        if timeline:
            entry.update(timeline)
        matches[match['id']] = entry
        if match.get('season') != catalogue['season'] or match.get('competition') != competition:
            continue
        stats = {row['side']: row.get('values', {}) for row in detail.get('statistics', [])}
        for side in ('home', 'away'):
            club = match[side]
            team = teams.setdefault(club, {'matches': 0, 'statMatches': 0, 'totals': dict.fromkeys(TEAM_STATS, 0.0),
                                           'scoredFirst': {'w': 0, 'd': 0, 'l': 0}, 'concededFirst': {'w': 0, 'd': 0, 'l': 0}})
            team['matches'] += 1
            values = {key: number(stats.get(side, {}).get(key)) for key in TEAM_STATS}
            if values['totalShots'] is not None and values['possessionPct'] is not None:
                team['statMatches'] += 1
                for key, value in values.items():
                    team['totals'][key] += value or 0
            if timeline and timeline['firstGoal']:
                team['scoredFirst' if timeline['firstGoal'] == side else 'concededFirst'][outcome(match, side)] += 1
            for p in detail.get('lineups', {}).get(side, {}).get('players', []):
                if not p.get('played'):
                    continue
                row = players.setdefault(p['espnId'], {'espnId': p['espnId'], 'playerCode': p.get('playerCode'), 'name': p['name'], 'team': club,
                                                       'appearances': 0, 'starts': 0, 'minutes': 0, 'goals': 0, 'assists': 0,
                                                       'yellowCards': 0, 'redCards': 0, 'substituteGoals': 0, 'lastDate': ''})
                if match['date'] >= row['lastDate']:
                    row.update(team=club, lastDate=match['date'], name=p['name'], playerCode=p.get('playerCode') or row['playerCode'])
                goals = int(p.get('goals') or 0)
                row['appearances'] += 1
                row['starts'] += int(bool(p.get('starter')))
                row['minutes'] += int(p.get('minutes') or 0)
                row['goals'] += goals
                row['assists'] += int(p.get('assists') or 0)
                row['yellowCards'] += int(p.get('yellowCards') or 0)
                row['redCards'] += int(p.get('redCards') or 0)
                row['substituteGoals'] += 0 if p.get('starter') else goals
    for team in teams.values():
        count = team.pop('statMatches')
        totals = team.pop('totals')
        team['statMatches'] = count
        team['averages'] = {key: round(value / count, 2) for key, value in totals.items()} if count else {}
        team['totals'] = {key: round(totals[key]) for key in ['yellowCards', 'redCards', 'totalShots', 'shotsOnTarget', 'wonCorners', 'foulsCommitted', 'saves']} if count else {}
    for row in players.values():
        row.pop('lastDate')
    season_covered = sum(t['matches'] for t in teams.values()) // 2
    return {'version': 1, 'league': league, 'season': catalogue['season'], 'updatedAt': datetime.now(timezone.utc).isoformat(),
            'coveredMatches': season_covered, 'targetMatches': target, 'matches': matches, 'teams': teams,
            'players': sorted(players.values(), key=lambda r: (-r['goals'], -r['assists'], r['name'])),
            'basis': '由已收录比赛的出场名单与技术统计汇总；半场比分与先进球方仅在事件进球数与终场比分一致时给出。'}
