from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from football import racing_preparation as prep
from football.files import publish

AT = datetime(2026, 11, 21, 4, tzinfo=timezone.utc)
ID = 'HK_2022_H459'


def inputs():
    entry = {'id': ID, 'name': '样本马', 'number': '1', 'rating': 63}
    race = {'id': '2026-11-22-ST-1', 'date': '2026-11-22', 'offTime': '2026-11-22T13:00:00+08:00',
            'class': '第三班', 'status': 'scheduled', 'entries': [entry], 'source': 'https://racing.hkjc.com/race'}
    horse = {'id': ID, 'name': '样本马', 'profile': {'現時評分': '63'}, 'records': [
        {'date': '2026-11-10', 'rating': 65, 'class': '3', 'place': 8, 'raceId': '2026-11-10-HV-1'},
        {'date': '2026-10-20', 'rating': 68, 'class': '3', 'place': 6, 'raceId': '2026-10-20-HV-1'},
        {'date': '2026-10-01', 'rating': 70, 'class': '3', 'place': 7, 'raceId': '2026-10-01-HV-1'}]}
    rows = [{'date': (AT.date() - timedelta(days=i)).isoformat(), 'type': '快操' if i in [1, 3, 5, 12] else '踱步',
             'track': '沙田', 'details': '一次操练'} for i in range(1, 23)]
    research = {'workouts': {'horseId': ID, 'fetchedAt': AT.isoformat(), 'source': 'https://racing.hkjc.com/workouts', 'records': rows}}
    return entry, horse, research, race


def test_recent_work_compares_equal_weekly_exposure_and_class_boundary():
    e, h, w, race = inputs()
    result = prep.runner(e, h, w, AT, race)
    assert result['known'] and result['activity'] == '近期加紧备战'
    assert result['days7'] == 7 and result['days14'] == 14
    assert result['counts7']['fast'] == 3 and result['counts14']['fast'] == 1
    assert result['classWatch']['gap'] == 3
    assert result['classWatch']['change'] == -7
    assert result['classWatch']['watch'] is True


def test_duplicates_races_same_day_and_future_are_excluded():
    e, h, w, race = inputs()
    raw = w['workouts']['records']
    raw += [deepcopy(raw[0]), {'date': '2026-11-20', 'type': '出賽'},
            {'date': '2026-11-21', 'type': '快操'}, {'date': '2026-11-23', 'type': '試閘'}]
    h['records'].insert(0, {'date': race['date'], 'rating': 1, 'class': '5'})
    result = prep.runner(e, h, w, AT, race)
    assert result['counts7']['fast'] == 3 and result['days7'] == 7
    assert len(result['workouts']) == 21
    assert result['classWatch']['change'] == -7


@pytest.mark.parametrize('fault', ['missing', 'stale', 'future_fetch', 'wrong_horse', 'short_history', 'unknown_type'])
def test_incomplete_or_unreliable_training_never_becomes_negative_intent(fault):
    e, h, w, race = inputs()
    if fault == 'missing':
        w = {}
    elif fault == 'stale':
        w['workouts']['fetchedAt'] = (AT - timedelta(days=4)).isoformat()
    elif fault == 'future_fetch':
        w['workouts']['fetchedAt'] = (AT + timedelta(hours=1)).isoformat()
    elif fault == 'wrong_horse':
        w['workouts']['horseId'] = 'HK_2022_H460'
    elif fault == 'short_history':
        w['workouts']['records'] = w['workouts']['records'][:7]
    else:
        w['workouts']['records'][0]['type'] = '未知类型'
    result = prep.runner(e, h, w, AT, race)
    assert not result['known'] and result['activity'] == '资料不足'


def test_reduced_work_after_a_race_is_not_interpreted_as_unwillingness():
    e, h, w, race = inputs()
    w['workouts']['records'] = [r for r in w['workouts']['records'] if r['date'] <= '2026-11-13']
    result = prep.runner(e, h, w, AT, race)
    assert result['activity'] == '近期操练减少'
    h['records'][0]['date'] = '2026-11-18'
    assert prep.runner(e, h, w, AT, race)['activity'] == '赛后调整期'


def test_observation_window_does_not_include_uncollected_days():
    e, h, w, race = inputs()
    w['workouts']['fetchedAt'] = (AT - timedelta(days=1)).isoformat()
    result = prep.runner(e, h, w, AT, race)
    assert result['window']['to'] == '2026-11-19'
    assert all(r['date'] <= '2026-11-19' for r in result['workouts'])


def test_standard_boundary_is_not_a_promised_class_change():
    e, h, w, race = inputs()
    e['rating'] = 64
    assert not prep.runner(e, h, w, AT, race)['classWatch']['watch']
    e['rating'] = 60
    result = prep.runner(e, h, w, AT, race)['classWatch']
    assert result['gap'] == 0 and not result['watch']
    race['class'] = '第五班'
    assert prep.runner(e, h, w, AT, race)['classWatch']['threshold'] is None
    race['class'] = '三級賽'
    assert prep.runner(e, h, w, AT, race)['classWatch']['class'] is None
    race['class'] = '第三班'
    e['rating'] = None
    assert prep.runner(e, h, w, AT, race)['classWatch']['gap'] is None


@pytest.fixture
def environment(tmp_path, monkeypatch):
    e, h, w, race = inputs()
    class Clock(datetime):
        current = AT
        @classmethod
        def now(cls, tz=None):
            return cls.current.astimezone(tz) if tz else cls.current.replace(tzinfo=None)
    monkeypatch.setattr(prep, 'datetime', Clock)
    monkeypatch.setattr(prep, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(prep, 'FOLDER', tmp_path / 'racing')
    monkeypatch.setattr(prep, 'get_race', lambda ident: race)
    monkeypatch.setattr(prep, 'read_control', lambda: {'enabled': True})
    publish(prep.FOLDER / 'horses' / (ID + '.json'), h)
    publish(prep.FOLDER / 'research' / (ID + '.json'), w)
    return race, h, Clock


def test_saved_pre_race_observation_is_not_rewritten_after_result(environment):
    race, h, clock = environment
    before = prep.assessment(race['id'])
    path = prep.STATE / 'racing-preparation' / (race['id'] + '.json')
    original = path.read_bytes()
    race.update(status='finished', resultOfficial=True)
    race['entries'][0]['place'] = 8
    clock.current = AT + timedelta(days=5)
    h['records'].insert(0, {'date': '2026-11-25', 'rating': 60, 'class': '4', 'source': 'https://racing.hkjc.com/next'})
    publish(prep.FOLDER / 'horses' / (ID + '.json'), h)
    publish(prep.FOLDER / 'research' / (ID + '.json'), {})
    after = prep.assessment(race['id'])
    assert after['hasPregame'] and after['status'] == 'saved'
    assert after['runners'] == before['runners'] and path.read_bytes() == original
    actual = after['review']['runners'][0]
    assert actual['place'] == 8 and actual['ratingChange'] == -3 and actual['downClass'] is True
    assert 'successRate' not in after['review']


def test_finished_without_snapshot_never_claims_a_pregame_forecast(environment):
    race, h, clock = environment
    race.update(status='finished', resultOfficial=True)
    clock.current = AT + timedelta(days=2)
    value = prep.assessment(race['id'])
    assert value['status'] == 'retrospective' and not value['hasPregame']
    assert not (prep.STATE / 'racing-preparation').exists()


def test_pause_prevents_fetch_and_snapshot_writes(environment, monkeypatch):
    from football import horse_research
    race, h, clock = environment
    monkeypatch.setattr(prep, 'read_control', lambda: {'enabled': False})
    monkeypatch.setattr(horse_research, 'get_research', lambda ident: pytest.fail('paused fetch'))
    value = prep.assessment(race['id'], refresh=True)
    assert value['paused'] and not value['hasPregame']
    assert not (prep.STATE / 'racing-preparation').exists()


def test_changed_race_time_and_tampered_snapshots_are_not_validated(environment):
    race, h, clock = environment
    prep.assessment(race['id'])
    race.update(status='finished', resultOfficial=True, offTime='2026-11-22T14:00:00+08:00')
    assert not prep.assessment(race['id'])['hasPregame']
    race['offTime'] = '2026-11-22T13:00:00+08:00'
    path = prep.STATE / 'racing-preparation' / (race['id'] + '.json')
    altered = prep.load(path)
    altered['runners'][0]['activity'] = 'altered'
    publish(path, altered)
    assert not prep.assessment(race['id'])['hasPregame']
