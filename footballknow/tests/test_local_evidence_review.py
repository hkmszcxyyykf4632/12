import copy

import pytest

from football import evidence_reviews as er, local_evidence_review as local


def football():
    d = er.new_dossier('football', 'fixture', {'score': [0, 1], 'scoreCandidates': [[0, 1], [1, 2]],
                      'asianSide': 'A', 'summary': ['主选客队，但换人作用仍待核实。']})
    d['fixture'] = {'home': '主队', 'away': '客队', 'homeGoals': 0, 'awayGoals': 3, 'scoreScope': '90分钟含补时'}
    s = er.add_source(d, 'https://example.org/match', '正式赛果')
    er.add_fact(d, '主队0:3客队', [s], category='result')
    d['originalQuote'] = {'market': 'asian-handicap', 'line': .5}
    er.add_fact(d, '原预测采用报价：主队受让半球，客队1.46', [s], category='market', before_event=True)
    events = []
    for clock, kind, before, after in [("10'", 'goal', [0, 0], [0, 1]), ("30'", 'goal', [0, 1], [0, 2]),
                                        ("90'", 'red-card', [0, 2], [0, 2]), ("90'+2'", 'penalty---scored', [0, 2], [0, 3])]:
        text = ('红牌' if kind == 'red-card' else '进球') + '；比分' + local.display(after)
        fid = er.add_fact(d, text, [s], time=clock, before_event=False)
        events.append({'clock': clock, 'type': kind, 'side': 'away', 'text': text, 'before': before, 'after': after, 'evidenceIds': [fid]})
    d['matchContext'] = {'events': events, 'goalsReconciled': True}
    return d


def test_public_generation_is_offline_cited_and_preserves_original(tmp_path, monkeypatch):
    monkeypatch.setattr(er, 'STATE', tmp_path)
    monkeypatch.setattr(er, 'request_json', lambda *a: pytest.fail('No external generation is permitted'))
    d = football()
    before = copy.deepcopy(d)
    result = er.build_review('football', 'fixture', d, True)
    assert result['analysisStatus'] == 'ready' and result['engine'] == 'local-evidence-1'
    audits = {c['claimId']: c for c in result['claimAudits']}
    assert audits['target-score']['verdict'] == 'contradicted'
    assert audits['target-asianSide']['verdict'] == 'supported'
    assert audits['c1']['verdict'] == 'unresolved'
    critical = next(c for c in result['drivers'] if '特殊事件' in c['title'])
    assert '事件前比分 0:2' in critical['explanation']
    assert '不能归因于该事件' in critical['explanation']
    assert any("10'" in c['explanation'] and "30'" in c['explanation'] for c in result['drivers'])
    assert d == before
    assert not any(c['category'] == 'method' for c in result['lessons'])
    assert er.build_review('football', 'fixture', d, True)['generatedAt'] == result['generatedAt']


@pytest.mark.parametrize('line,side,expected', [(-.25, 'H', '输半'), (.25, 'H', '赢半'), (0, 'A', '走盘'), (.5, 'A', '输盘')])
def test_quarter_handicap_uses_original_line(line, side, expected):
    d = football()
    d['fixture'].update(homeGoals=0, awayGoals=0)
    d['originalQuote']['line'] = line
    d['original']['asianSide'] = side
    d['claims'][-1]['value'] = side
    outcome = local.football_outcome(d)
    assert outcome['asian'] == expected


def test_unverified_or_postgame_quote_cannot_be_settled():
    d = football()
    next(f for f in d['facts'] if f['category'] == 'market')['beforeEvent'] = False
    assert local.football_outcome(d)['asian'] is None
    d['fixture']['scoreScope'] = '含点球大战'
    assert local.football_outcome(d) is None


def test_unreconciled_goals_never_become_a_progression():
    d = football()
    d['matchContext'] = {'goalsReconciled': False, 'events': []}
    result = er.validate_analysis(local.generate(d), d)
    assert not any('进球顺序' in c['title'] or '红牌、点球' in c['title'] for c in result['drivers'])


def test_racing_withdrawal_does_not_become_a_loss():
    d = er.new_dossier('racing', 'race', {'pick': 'horse1', 'summary': []})
    source = er.add_source(d, 'https://example.org/race', '正式赛果')
    fid = er.add_fact(d, '1号退出', [source], category='result')
    d['raceContext'] = {'entries': [{'id': 'horse1', 'name': '一号马', 'number': 1, 'withdrawn': True, 'place': None, 'evidenceIds': [fid]}]}
    r = er.validate_analysis(local.generate(d), d)
    assert r['claimAudits'][0]['verdict'] == 'unresolved'


def test_immature_stock_horizon_cannot_be_called_a_failure():
    d = er.new_dossier('stocks', 'stock', {'week': 'up', 'quarter': 'down'})
    source = er.add_source(d, 'https://example.org/prices', '收盘价')
    for label in ('短期', '中期'):
        er.add_fact(d, label + '观察中，未到期', [source], category='outcome')
    d['priceContext'] = {'horizons': {'week': {'correct': None}, 'quarter': {'correct': None}}}
    r = er.validate_analysis(local.generate(d), d)
    assert all(c['verdict'] == 'unresolved' for c in r['claimAudits'])
