import pytest

from football import horse_research as research
from football.files import publish


def workout_html(brand='D241'):
    return f'''<div class="horseProfile"><span class="title_text">香港精神 ({brand})</span></div>
    <table class="table_bd"><thead><tr><td>晨操類別</td></tr></thead><tbody>
    <tr><td>12/11/2026</td><td>快操</td><td>沙田 全天候</td><td>30.2 26.1 (56.3) (助手) 大才</td><td></td></tr>
    <tr><td>23/10/2026</td><td>試閘</td><td>從化 草地</td><td>第6組 (梁家俊) 1600M 捷足奔馳 25.8 22.8 25.3 24.5 (1.38.41)</td><td>B</td></tr>
    </tbody></table>'''


def sectional_html():
    return '''<p>賽事日期: 14/11/2026, 沙田</p><img src="/racecard_rt_1_o.gif">
    <p>第 1 場 第四班 - 1200米 - 草地</p><table class="race_table"><tbody><tr>
    <td>1</td><td>12</td><td><a href="/zh-hk/local/information/horse?horseid=HK_2025_L438">精算無雙</a></td>
    <td><p><span>8</span><i>5-1/4</i></p><p>24.43</p></td>
    <td><p><span>7</span><i>4-1/2</i></p><p>22.36<span class="color_blue2"><span>11.11</span><span>11.25</span></span></p></td>
    <td><p><span>1</span><i>1</i></p><p>22.39<span class="color_blue2"><span>10.86</span><span>11.53</span></span></p></td>
    <td></td><td></td><td></td><td>1:09.18</td></tr></tbody></table>'''


def test_workout_preserves_times_without_inventing_distance():
    rows = research.parse_workouts(workout_html(), 'HK_2019_D241')['records']
    assert rows[0]['distance'] is None
    assert rows[0]['publishedTime'] == '56.3'
    assert rows[1]['distance'] == 1600
    assert rows[1]['rider'] == '梁家俊'
    assert rows[1]['publishedTime'] == '1.38.41'
    with pytest.raises(ValueError):
        research.parse_workouts(workout_html('D242'), 'HK_2019_D241')


def test_sectional_identity_and_nested_200m_splits():
    value = research.parse_sectionals(sectional_html(), '2026-11-14-ST-1')
    splits = value['horses'][0]['splits']
    assert sum(s['seconds'] for s in splits) == pytest.approx(69.18)
    assert [s['metres'] for s in splits] == [400, 400, 400]
    assert splits[-1]['sub200'] == [10.86, 11.53]
    for ident in ['2026-11-14-HV-1', '2026-11-14-ST-2', '2026-11-13-ST-1']:
        with pytest.raises(ValueError):
            research.parse_sectionals(sectional_html(), ident)


def test_pause_keeps_cache_and_does_not_fetch(tmp_path, monkeypatch):
    monkeypatch.setattr(research, 'FOLDER', tmp_path)
    monkeypatch.setattr(research, 'read_control', lambda: {'enabled': False})
    monkeypatch.setattr(research, 'fetch_text', lambda url: pytest.fail('paused source fetched'))
    publish(tmp_path / 'horses/HK_2019_D241.json', {'id': 'HK_2019_D241'})
    publish(tmp_path / 'research/HK_2019_D241.json', {'workouts': {'fetchedAt': '2026-01-01', 'records': []}})
    result = research.get_research('HK_2019_D241')
    assert result['paused']
    assert result['workouts']['fetchedAt'] == '2026-01-01'
    with pytest.raises(LookupError):
        research.get_research('../bad')


def test_source_failure_keeps_prior_workouts(tmp_path, monkeypatch):
    monkeypatch.setattr(research, 'FOLDER', tmp_path)
    monkeypatch.setattr(research, 'read_control', lambda: {'enabled': True})
    def failed(url):
        raise OSError('offline')
    monkeypatch.setattr(research, 'fetch_text', failed)
    publish(tmp_path / 'horses/HK_2019_D241.json', {'records': []})
    publish(tmp_path / 'research/HK_2019_D241.json', {'workouts': {'fetchedAt': '2026-01-01', 'records': [{'date': '2025-12-31'}]}})
    research.refresh('HK_2019_D241')
    result = research.load(tmp_path / 'research/HK_2019_D241.json')
    assert result['errors']
    assert result['workouts']['fetchedAt'] == '2026-01-01'
    assert len(result['workouts']['records']) == 1
