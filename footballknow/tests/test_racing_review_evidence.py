import copy
import json

import pytest

from football import racing_analysis as analysis
from football import racing_review_evidence as evidence
from football.files import publish


@pytest.fixture
def sample(tmp_path, monkeypatch):
    race = {'id': '2026-11-18-HV-1', 'date': '2026-11-18', 'course': 'HV', 'distance': 1200,
            'status': 'finished', 'resultOfficial': True, 'offTime': '2026-11-18T12:00:00+00:00',
            'source': 'https://racing.hkjc.com/zh-hk/local/information/localresults',
            'updatedAt': '2026-11-18T12:30:00+00:00', 'entries': [
                {'id': 'HK_2023_J001', 'number': '1', 'name': '原首选', 'place': 2, 'position': '2',
                 'running': '1 1 2', 'finishTime': '1:10.25', 'winOdds': 3.2},
                {'id': 'HK_2023_J002', 'number': '2', 'name': '冠军', 'place': 1, 'position': '1',
                 'running': '2 2 1', 'finishTime': '1:10.00', 'winOdds': 8.1}]}
    monkeypatch.setattr(evidence, 'FOLDER', tmp_path / 'racing')
    monkeypatch.setattr(analysis, 'FOLDER', tmp_path / 'racing')
    monkeypatch.setattr(analysis, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(analysis, 'get_race', lambda ident: race)
    publish(evidence.FOLDER / 'races' / (race['id'] + '.json'), race)
    return race


def sectionals(race):
    return {'raceId': race['id'], 'date': race['date'], 'course': '跑馬地', 'distance': 1200,
            'source': 'https://racing.hkjc.com/sectionals', 'fetchedAt': race['updatedAt'],
            'horses': [{'horseId': e['id'], 'position': e['position'], 'finishTime': e['finishTime'],
                        'splits': [{'metres': 400, 'seconds': s, 'position': e['place']} for s in [24, 23, 23]]}
                       for e in race['entries']]}


@pytest.mark.parametrize('fault', ['raceId', 'date', 'course', 'distance', 'horseId', 'position'])
def test_sectionals_reject_other_race_or_inconsistent_runner(sample, fault):
    raw = sectionals(sample)
    if fault in ('horseId', 'position'):
        raw['horses'][0][fault] = 'HK_2023_J999' if fault == 'horseId' else '1'
    else:
        raw[fault] = {'raceId': '2026-11-18-HV-2', 'date': '2026-11-17', 'course': 'ST', 'distance': 1650}[fault]
    publish(evidence.FOLDER / 'sectionals' / (sample['id'] + '.json'), raw)
    dossier = evidence.build_dossier(sample, None)
    facts = [f for f in dossier['facts'] if f['category'] == 'sectionals']
    assert not facts
    assert any('分段' in gap for gap in dossier['gaps'])


def test_only_exact_same_race_horse_records_are_used(sample):
    horse = sample['entries'][0]
    base = {'raceId': sample['id'], 'date': sample['date'], 'course': '跑马地', 'distance': 1200,
            'place': 2, 'position': '2', 'equipment': 'B', 'source': sample['source']}
    records = [{**base, 'raceId': '2026-11-18-HV-2', 'equipment': 'WRONG_SAME_DAY'},
               {**base, 'raceId': '2026-11-11-HV-1', 'date': '2026-11-11', 'equipment': 'OLD'}, base]
    publish(evidence.FOLDER / 'horses' / (horse['id'] + '.json'),
            {'id': horse['id'], 'records': records, 'updatedAt': sample['updatedAt']})
    publish(evidence.FOLDER / 'research' / (horse['id'] + '.json'),
            {'sectionals': [{**base, 'splits': [{'seconds': 999, 'metres': 1200}]}]})
    dossier = evidence.build_dossier(sample, None)
    text = json.dumps(dossier, ensure_ascii=False)
    assert '本场装备 B' in text
    assert 'WRONG_SAME_DAY' not in text and 'OLD' not in text and '999' not in text
    assert not any(f['category'] == 'sectionals' for f in dossier['facts'])


def test_all_runners_and_verified_same_distance_sectionals_have_sources(sample):
    publish(evidence.FOLDER / 'sectionals' / (sample['id'] + '.json'), sectionals(sample))
    dossier = evidence.build_dossier(sample, {'pick': sample['entries'][0]['id'], 'summary': ['前置有利']})
    section_facts = [f for f in dossier['facts'] if f['category'] == 'sectionals']
    assert len(section_facts) == 2
    assert '2/2' in json.dumps(dossier, ensure_ascii=False)
    assert all(f['sourceIds'] for f in dossier['facts'])
    assert all(any(e['name'] in f['text'] for f in dossier['facts']) for e in sample['entries'])
    assert all(t['evidenceIds'] for t in dossier['timeline'])


def test_no_original_or_odds_history_cannot_invent_prediction_or_causes(sample):
    dossier = evidence.build_dossier(sample, None)
    assert dossier['original'] is None and not dossier['claims']
    assert any('赛前预测' in gap for gap in dossier['gaps'])
    assert any('赔率' in gap for gap in dossier['gaps'])
    assert any('竞赛' in gap for gap in dossier['gaps'])
    observed = '\n'.join(f['text'] for f in dossier['facts'])
    assert '资金流入' not in observed and '受阻' not in observed and '开盘' not in observed


def test_odds_first_sample_is_not_opening_or_complete_history(sample):
    sample['pools'] = [{'type': 'WIN', 'sourceUpdatedAt': '2026-11-18T11:59:00+00:00',
                        'checkedAt': '2026-11-18T11:59:20+00:00', 'quotes': [
                            {'combination': '1', 'first': '5', 'firstAt': '2026-11-18T11:00:00+00:00', 'value': '3.5'}]}]
    dossier = evidence.build_dossier(sample, None)
    odds = '\n'.join(f['text'] for f in dossier['facts'] if f['category'] == 'odds')
    assert '首次记录' in odds and '5' in odds and '3.5' in odds
    assert '开盘赔率' not in odds and '封盘赔率' not in odds
    assert any('完整' in gap and '赔率' in gap for gap in dossier['gaps'])
    sample['pools'][0]['quotes'][0]['firstAt'] = '2026-11-18T12:01:00+00:00'
    dossier = evidence.build_dossier(sample, None)
    assert not any('首次记录' in f['text'] for f in dossier['facts'])


@pytest.mark.parametrize('fault', ['unknown_start', 'late_source', 'retained', 'naive_stamp'])
def test_odds_without_verifiable_pre_race_order_has_no_movement_fact(sample, fault):
    sample['pools'] = [{'type': 'WIN', 'sourceUpdatedAt': '2026-11-18T11:59:00+00:00',
                        'quotes': [{'combination': '1', 'first': '5', 'firstAt': '2026-11-18T11:00:00+00:00', 'value': '3.5'}]}]
    if fault == 'unknown_start':
        sample['offTime'] = None
    elif fault == 'late_source':
        sample['pools'][0]['sourceUpdatedAt'] = '2026-11-18T12:00:00+00:00'
    elif fault == 'retained':
        sample['pools'][0]['quoteRetained'] = True
    else:
        sample['pools'][0]['sourceUpdatedAt'] = '2026-11-18T11:59:00'
    dossier = evidence.build_dossier(sample, None)
    assert not any('3.5' in f['text'] for f in dossier['facts'] if f['category'] == 'odds')


def test_public_finished_requires_official_and_replaces_legacy_without_mutating_pre(sample, monkeypatch):
    original = {'pick': sample['entries'][0]['id'], 'shortlist': [sample['entries'][0]['id']],
                'summary': ['原始预测'], 'details': []}
    with analysis.connect() as db:
        db.execute('INSERT INTO reports VALUES (?,?,?,?,?,?)',
                   (sample['id'], 'pre', '2026-11-18T10:00:00+00:00', 'old', 'fixed', json.dumps(original)))
        db.execute('INSERT INTO reports VALUES (?,?,?,?,?,?)',
                   (sample['id'], 'post', sample['updatedAt'], 'old', 'legacy', json.dumps({'summary': ['旧复盘']})))
    with analysis.connect() as db:
        before = dict(db.execute("SELECT * FROM reports WHERE phase='pre'").fetchone())
    calls = []
    def review(domain, identity, dossier, generate=False):
        calls.append(generate)
        return {'version': 2, 'analysisStatus': 'ready' if generate else 'facts_ready', 'dossier': dossier}
    monkeypatch.setattr(analysis, 'build_review', review)
    monkeypatch.setattr(analysis, 'model_report', lambda *args: pytest.fail('legacy model called'))
    status = analysis.public_status(sample['id'])
    assert status['reports']['post']['version'] == 2
    assert status['reports']['legacyPost']['snapshotHash'] == 'legacy'
    result = analysis.generate(sample['id'], 'post')
    assert True in calls and result['reports']['post']['analysisStatus'] == 'ready'
    with analysis.connect() as db:
        after = dict(db.execute("SELECT * FROM reports WHERE phase='pre'").fetchone())
    assert after == before
    sample['resultOfficial'] = False
    with pytest.raises(ValueError, match='正式'):
        analysis.generate(sample['id'], 'post')
    assert analysis.public_status(sample['id'])['reports']['post']['snapshotHash'] == 'legacy'


def test_dossier_does_not_mutate_original_or_race(sample):
    original = {'pick': sample['entries'][0]['id'], 'summary': ['原始选择'], 'preparationSnapshot': {'runners': []}}
    before = copy.deepcopy((sample, original))
    evidence.build_dossier(sample, original)
    assert (sample, original) == before


@pytest.mark.parametrize('off_time', ['2026-11-18T12:00:00+00:00', None])
def test_collection_refresh_reuses_review_but_changed_odds_create_revision(sample, tmp_path, monkeypatch, off_time):
    from football import evidence_reviews as reviews
    monkeypatch.setattr(reviews, 'STATE', tmp_path / 'review-state')
    sample['offTime'] = off_time
    calls = []
    def reply(rules, dossier, tokens):
        calls.append(dossier)
        return {'summary': ['Only recorded facts are available.'], 'claimAudits': [],
                'drivers': [], 'lessons': [], 'marketReview': []}
    monkeypatch.setattr(reviews, 'request_json', reply)
    first_dossier = evidence.build_dossier(sample, None)
    first = reviews.build_review('racing', sample['id'], first_dossier, generate=True)
    sample['updatedAt'] = '2026-11-19T12:30:00+00:00'
    refreshed = evidence.build_dossier(sample, None)
    second = reviews.build_review('racing', sample['id'], refreshed, generate=True)
    assert refreshed['facts'] == first_dossier['facts']
    assert refreshed['sources'][0]['updatedAt'] == sample['updatedAt']
    assert refreshed['sources'][0]['updatedAt'] != first_dossier['sources'][0]['updatedAt']
    assert first['revision'] == second['revision'] and second['analysisStatus'] == 'ready'
    assert len(calls) == 1
    sample['entries'][0]['winOdds'] = 3.3
    changed = reviews.build_review('racing', sample['id'], evidence.build_dossier(sample, None), generate=True)
    assert changed['revision'] != first['revision'] and len(calls) == 2
