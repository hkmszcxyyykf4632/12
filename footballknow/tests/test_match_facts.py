from football.match_facts import build_facts, clock_minute, score_timeline


def player(pid, name, starter=True, **extra):
    return {'espnId': pid, 'name': name, 'playerCode': None, 'starter': starter, 'played': True, 'minutes': 90 if starter else 20,
            'goals': 0, 'assists': 0, 'yellowCards': 0, 'redCards': 0, **extra}


def detail(events, home_players, away_players, stats=True):
    values = {'possessionPct': '60', 'totalShots': '10', 'shotsOnTarget': '4', 'yellowCards': '2'}
    return {'status': 'available', 'venue': 'Ground', 'attendance': 100, 'events': events,
            'lineups': {'home': {'players': home_players}, 'away': {'players': away_players}},
            'statistics': [{'side': 'home', 'values': values}, {'side': 'away', 'values': {**values, 'possessionPct': '40'}}] if stats else []}


def goal(side, clock, period, kind='goal'):
    return {'type': kind, 'side': side, 'clock': clock, 'period': period, 'players': []}


CATALOGUE = {'season': '2026/27'}


def match(mid, home, away, hg, ag, **extra):
    return {'id': mid, 'date': mid[:10], 'home': home, 'away': away, 'homeGoals': hg, 'awayGoals': ag,
            'season': '2026/27', 'competition': '英超', 'finished': True, **extra}


def test_clock_and_timeline_are_only_reported_when_goals_reconcile():
    assert clock_minute("45'+2'") == 47.5 and clock_minute("7'") == 7 and clock_minute('') is None
    m = match('2026-09-01|A|B', 'A', 'B', 2, 1)
    events = [goal('away', "12'", 1), goal('home', "45'+1'", 1, 'own-goal'), goal('home', "70'", 2, 'penalty---scored')]
    assert score_timeline(m, {'events': events}) == {'halfTime': [1, 1], 'firstGoal': 'away'}
    assert score_timeline(m, {'events': events[:2]}) is None, 'a missing goal must not produce a half-time score'


def test_unknown_goal_time_or_period_does_not_invent_the_opener():
    m = match('2026-09-01|A|B', 'A', 'B', 1, 1)
    events = [goal('home', None, 1), goal('away', "40'", 1)]
    assert score_timeline(m, {'events': events}) == {'halfTime': [1, 1], 'firstGoal': None}
    events[0]['period'] = None
    assert score_timeline(m, {'events': events}) is None
    assert clock_minute('unknown+5') is None


def test_players_and_teams_are_totalled_for_the_season_competition_only():
    a = [player('1', 'Ann', goals=2, assists=0, yellowCards=1), player('2', 'Sub', starter=False, goals=1)]
    b = [player('3', 'Bea', redCards=1)]
    pairs = [
        (match('2026-09-01|A|B', 'A', 'B', 3, 0), detail([goal('home', "5'", 1), goal('home', "50'", 2), goal('home', "80'", 2)], a, b)),
        (match('2026-09-08|B|A', 'B', 'A', 1, 1), detail([goal('home', "9'", 1), goal('away', "60'", 2)], b, [player('1', 'Ann', goals=1)])),
        (match('2025-09-08|B|A', 'B', 'A', 4, 0, season='2025/26'), detail([], b, a)),
        (match('2026-09-15|A|B', 'A', 'B', 1, 0), {'status': 'unavailable'}),
    ]
    facts = build_facts('epl', CATALOGUE, '英超', pairs, 10)
    assert facts['coveredMatches'] == 2 and facts['targetMatches'] == 10
    ann = facts['players'][0]
    assert (ann['name'], ann['goals'], ann['appearances'], ann['starts'], ann['minutes'], ann['yellowCards']) == ('Ann', 3, 2, 2, 180, 1)
    sub = next(p for p in facts['players'] if p['name'] == 'Sub')
    assert sub['substituteGoals'] == 1 and sub['starts'] == 0
    team_a, team_b = facts['teams']['A'], facts['teams']['B']
    assert team_a['scoredFirst'] == {'w': 1, 'd': 0, 'l': 0} and team_a['concededFirst'] == {'w': 0, 'd': 1, 'l': 0}
    assert team_b['scoredFirst'] == {'w': 0, 'd': 1, 'l': 0}
    assert team_a['averages']['possessionPct'] == 50 and team_a['totals']['yellowCards'] == 4
    assert facts['matches']['2026-09-01|A|B']['halfTime'] == [1, 0]
    assert '2025-09-08|B|A' in facts['matches'] and 'halfTime' not in facts['matches']['2025-09-08|B|A']
    assert '2026-09-15|A|B' not in facts['matches']
