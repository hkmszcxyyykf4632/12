import copy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from football import racing, racing_analysis as analysis


def race():
    return {'id': '2026-11-18-HV-1', 'date': '2026-11-18', 'status': 'scheduled',
            'offTime': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            'entries': [{'id': 'HK_2023_J463', 'name': '禾道威', 'withdrawn': False},
                        {'id': 'HK_2024_K500', 'name': '另一匹', 'withdrawn': True}]}


def content(phase='pre'):
    return {'summary': ['首段结论。', '次段依据。'], 'pick': 'HK_2023_J463' if phase == 'pre' else None,
            'shortlist': ['HK_2023_J463'] if phase == 'pre' else [], 'details': [{'title': '依据', 'text': '已提供的赛绩。'}]}


def test_horse_identity_and_suitability_do_not_mix_withdrawals_or_courses():
    html = '''<span class="title_text">禾道威 (J463)</span><table class="table_top_right">
    <tr><td>父系</td><td>:</td><td>Starspangledbanner</td></tr>
    <tr><td>母系</td><td>:</td><td>Victoria's Angel</td></tr>
    <tr><td>外祖父</td><td>:</td><td>Dark Angel</td></tr></table>'''
    value = racing.parse_horse(html, 'HK_2023_J463')
    assert value['pedigree']['damsire'] == 'Dark Angel'
    with pytest.raises(ValueError, match='身份'):
        racing.parse_horse(html, 'HK_2024_K500')
    rows = [{'course': '沙田', 'surface': '草地', 'distance': 1200, 'going': '好', 'place': p} for p in [1, 2, None]]
    rows += [{'course': '沙田', 'surface': '草地', 'place': 1, 'withdrawn': True},
             {'course': '跑马地', 'surface': '草地', 'place': 6}]
    groups = racing.suitability(rows)
    assert groups['course'][0] == {'label': '沙田', 'starts': 3, 'wins': 1, 'top3': 2, 'lowSample': True}
    assert groups['course'][1]['starts'] == 1
    assert racing.placing('1 DH') == 1 and racing.placing('WV') is None


def test_pre_race_cannot_cross_start_or_pick_a_withdrawn_horse():
    value = race()
    analysis.check_phase(value, 'pre', datetime.now(timezone.utc))
    with pytest.raises(ValueError, match='开赛'):
        analysis.check_phase(value, 'pre', datetime.fromisoformat(value['offTime']))
    bad = content(); bad['pick'] = bad['shortlist'][0] = 'HK_2024_K500'
    with pytest.raises(ValueError, match='名单'):
        analysis.validate_content(bad, value, 'pre')
    with pytest.raises(ValueError, match='赛后'):
        analysis.validate_content(content(), value, 'post')
    assert analysis.outcome(content(), value)['status'] == 'pending'
    value['status'] = 'finished'; value['entries'][0]['withdrawn'] = True
    assert analysis.outcome(content(), value)['status'] == 'void'


def test_forecasts_are_immutable_and_post_race_reviews_do_not_inflate_score(tmp_path, monkeypatch):
    value = race()
    monkeypatch.setattr(analysis, 'STATE', tmp_path)
    monkeypatch.setattr(analysis, 'get_race', lambda ident: value)
    monkeypatch.setattr(analysis, 'settings', lambda: SimpleNamespace(model='test-model'))
    def cached(path):
        return value if path.parent.name == 'races' else {'profile': {'父系': 'Known'}, 'records': []}
    monkeypatch.setattr(analysis, 'load', cached)
    calls = []
    def reply(rules, context, tokens):
        calls.append(context['phase'])
        return content(context['phase'])
    monkeypatch.setattr(analysis, 'request_json', reply)
    first = analysis.generate(value['id'], 'pre')['reports']['pre']
    assert analysis.generate(value['id'], 'pre')['reports']['pre'] == first
    assert calls == ['pre']
    value['status'] = 'finished'; value['entries'][0].update(place=1, position='1')
    final = analysis.generate(value['id'], 'post')
    assert final['reports']['pre'] == first
    assert final['evaluation']['published'] == final['evaluation']['wins'] == final['evaluation']['evaluated'] == 1
    assert set(final['reports']) == {'pre', 'post'}


def test_model_finishing_after_off_is_never_saved_as_a_prediction(tmp_path, monkeypatch):
    value = race()
    monkeypatch.setattr(analysis, 'STATE', tmp_path)
    monkeypatch.setattr(analysis, 'get_race', lambda ident: value)
    monkeypatch.setattr(analysis, 'load', lambda path: {'profile': {'父系': 'Known'}, 'records': []})
    def late_reply(*args):
        value['offTime'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        return content()
    monkeypatch.setattr(analysis, 'request_json', late_reply)
    with pytest.raises(ValueError, match='开赛'):
        analysis.generate(value['id'], 'pre')
    assert analysis.public_status(value['id'])['evaluation']['published'] == 0


def test_paused_horse_lookup_never_fetches_and_paths_are_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(racing, 'FOLDER', tmp_path)
    monkeypatch.setattr(racing, 'read_control', lambda: {'enabled': False})
    monkeypatch.setattr(racing, 'fetch_text', lambda url: pytest.fail('paused'))
    assert racing.horse_detail('HK_2023_J463')['paused'] is True
    with pytest.raises(LookupError):
        racing.horse_detail('../private')
    with pytest.raises(LookupError):
        racing.get_race('../private')
