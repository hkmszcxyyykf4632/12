from copy import deepcopy
from datetime import timedelta

from football import football_forecasts as ff, odds_signals as signals
from football.odds_forecast import build
from test_football_forecasts import AT, fixture, research, sandbox


def test_no_change_does_not_create_prediction(sandbox):
    sandbox['quotes'][1]['line'] = sandbox['quotes'][0]['line']
    assert not ff.generate(sandbox, 'initial')
    assert ff.status(sandbox)['stages']['initial']['report'] is None
    assert '没有可核对的赔率变化' in ff.status(sandbox)['stages']['initial']['message']


def test_different_providers_and_inplay_are_not_comparable(sandbox):
    sandbox['quotes'][1]['provider'] = 'Other'
    signals.observe([sandbox], AT)
    assert not signals.analyse(sandbox, AT)['eligible']
    sandbox['quotes'][0]['inPlay'] = True
    assert not signals.analyse(sandbox, AT)['eligible']


def test_first_observation_is_not_called_opening(sandbox):
    sandbox['quotes'] = sandbox['quotes'][:1]
    signals.observe([sandbox], AT)
    later = deepcopy(sandbox)
    later['quotes'][0].update(fetchedAt=(AT+timedelta(minutes=1)).isoformat(), line=-1)
    signals.observe([later], AT+timedelta(minutes=1))
    change = signals.analyse(later, AT+timedelta(minutes=1))['primary']
    assert change['basis'] == 'first-observed' and change['side'] == 'H'
    assert change['before']['line'] == -.75 and change['after']['line'] == -1


def test_same_opponent_same_venue_can_trigger_without_current_opening(sandbox):
    old = deepcopy(sandbox)
    old.update(id='122', kickoff=(AT-timedelta(days=100)).isoformat(), finished=True)
    old['quotes'] = [{**old['quotes'][0], 'line': -.25, 'fetchedAt': (AT-timedelta(days=101)).isoformat()}]
    signals.observe([old], AT)
    sandbox['quotes'] = sandbox['quotes'][:1]
    assert signals.analyse(sandbox, AT)['primary']['basis'] == 'same-opponent-same-venue'
    sandbox['teams']['home'], sandbox['teams']['away'] = sandbox['teams']['away'], sandbox['teams']['home']
    assert not signals.analyse(sandbox, AT)['eligible']


def test_statistical_model_saves_two_consistent_scores_without_external_ai(sandbox, monkeypatch):
    monkeypatch.setattr(ff, 'build_prediction', build)
    assert ff.generate(sandbox, 'initial')
    r = ff.status(sandbox)['stages']['initial']['report']
    assert r['model'] == signals.VERSION and r['asianSide'] == 'H'
    assert len(r['scoreCandidates']) == len({tuple(s) for s in r['scoreCandidates']}) == 2
    assert r['scoreCandidates'][0] == r['score']
    assert all(signals.profit(s, r['quote'], r['asianSide']) >= 0 for s in r['scoreCandidates'])
    assert r['oddsSignal']['before']['line'] == -.5
    sandbox.update(finished=True, started=True, state='finished')
    for side, n in zip(('home', 'away'), r['scoreCandidates'][1]):
        sandbox['teams'][side]['goals'] = n
    assert ff.review(r, sandbox, detailed=False)['exactScore'] is True


def test_half_ball_underdog_can_win_outright_not_only_draw(sandbox):
    snapshot = {'match': sandbox, 'baseline': ff.baseline(research(sandbox), AT),
        'quote': {**sandbox['quotes'][0], 'line': -.5}, 'research': research(sandbox), 'at': AT,
        'cutoff': AT+timedelta(hours=1), 'oddsSignal': {'eligible': True, 'primary': {
            'market': 'asian-handicap', 'side': 'A', 'basis': 'opening', 'lineChange': 0,
            'weightChangesPP': {'H': -2, 'A': 2},
            'before': {**sandbox['quotes'][0], 'line': -.5},
            'after': {**sandbox['quotes'][0], 'line': -.5}}}}
    result = build(snapshot)
    assert result['asianSide'] == 'A'
    assert all(s[0] <= s[1] for s in result['scoreCandidates'])
    assert signals.profit([0, 1], snapshot['quote'], 'A') > 0
