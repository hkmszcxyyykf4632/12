import json
import os
import sqlite3
from copy import deepcopy
from datetime import timedelta
from pathlib import Path

import pytest

from football import football_forecasts as ff
from test_football_forecasts import AT, content, research, sandbox


@pytest.mark.parametrize('text', [
    '未见改变小比分倾向关键证据，故比分沿用统计首选2-1仅作高球数侧调整。',
    '统计基线首选为2:1。',
    '基线的首选比分是2比1。',
    '初版首选1-1。',
])
def test_reject_explicit_misstatement_of_baseline_or_initial_score(text):
    value = content()
    value['summary'][1] = text
    with pytest.raises(ValueError, match='误述'):
        ff.validate(value, {'line': -1.5}, {'leadingScores': [[1, 1]]}, {'score': [2, 1]})


def test_baseline_explanation_is_deterministic_and_does_not_force_same_handicap_side():
    value = {**content(), 'asianSide': 'A'}
    value['summary'][1] = '统计首选1:1；本版主选2:1，客队+1.5与该比分相符。'
    report = ff.validate(value, {'line': -1.5}, {'leadingScores': [[1, 1]]}, {'score': [2, 1]})
    report['baseline'] = {'leadingScores': [[1, 1]]}
    explanation = ff.baseline_explanation(report)
    assert explanation['baselineScore'] == [1, 1]
    assert explanation['selectedScore'] == [2, 1]
    assert explanation['differsFromBaseline'] is True
    assert '不能称为沿用统计首选' in explanation['text']
    assert report['asianSide'] == 'A'


def test_bad_baseline_prose_never_saved_as_new_forecast(sandbox, monkeypatch):
    value = content()
    value['summary'][1] = '比分沿用统计首选2-1。'
    monkeypatch.setattr(ff, 'build_prediction', lambda *args: value)
    assert not ff.generate(sandbox, 'final')
    assert ff.status(sandbox)['stages']['final']['report'] is None


def test_append_only_correction_keeps_original_prediction_and_snapshot(sandbox, monkeypatch):
    r = research(sandbox)
    r['teams']['home'].update(name='曼城', comparisons={'previous': {'difference': {'retained': 8}}, 'headToHead': {'difference': {'retained': 7}}})
    r['teams']['home']['form'].update(summary='已收录比赛中连续1负；近10场6胜、2平、2负。', run=1, outcome='L')
    r['teams']['home']['lineup']['formation'] = '4-3-3'
    monkeypatch.setattr(ff, 'research_row', lambda row: r)
    assert ff.generate(sandbox, 'initial')
    assert ff.generate(sandbox, 'final')
    with ff.connect() as db:
        original = tuple(db.execute('SELECT content,snapshot FROM forecasts WHERE stage="final"').fetchone())
    amendment = ff.record_baseline_amendment(sandbox, 'final', '原文将2:1误述为统计首选；真实基线为1:1。')
    assert amendment['issuedAt'] == AT.isoformat()
    assert amendment['baselineExplanation']['baselineScore'] == [1, 1]
    assert amendment['initialPredictionScore'] == [2, 1]
    assert amendment['facts']['home']['run'] == 1
    assert amendment['facts']['home']['formSummary'].startswith('已收录比赛中连续1负')
    assert amendment['facts']['home']['formation'] == '4-3-3'
    assert amendment['facts']['home']['previousRetained'] == 8
    assert amendment['facts']['home']['headToHeadRetained'] == 7
    assert amendment['facts']['away']['previousRetained'] is None
    monkeypatch.setattr(ff, 'now', lambda: AT + timedelta(seconds=1))
    second = ff.record_baseline_amendment(sandbox, 'final', '补充核对：连续1负不等于连败。')
    with ff.connect() as db:
        assert tuple(db.execute('SELECT content,snapshot FROM forecasts WHERE stage="final"').fetchone()) == original
        assert db.execute('SELECT count(*) FROM forecast_amendments').fetchone()[0] == 2
        with pytest.raises(sqlite3.IntegrityError, match='append-only'):
            db.execute('UPDATE forecast_amendments SET content="{}"')
        with pytest.raises(sqlite3.IntegrityError, match='append-only'):
            db.execute('DELETE FROM forecast_amendments')
    report = ff.status(sandbox)['stages']['final']['report']
    assert report['score'] == [2, 1] and report['asianSide'] == 'H'
    assert [a['id'] for a in report['amendments']] == [amendment['id'], second['id']]
    assert ff.read_index()['matches']['123']['stages']['final']['report']['amendments'] == report['amendments']
    assert report['baselineExplanation'] == amendment['baselineExplanation']
    if os.environ.get('FORECAST_AMENDMENT_EVIDENCE_DIR'):
        target = Path(os.environ['FORECAST_AMENDMENT_EVIDENCE_DIR'])
        target.mkdir(parents=True, exist_ok=True)
        (target / 'amendment-example.json').write_text(json.dumps(amendment, ensure_ascii=False, indent=2), encoding='utf-8')
        (target / 'immutability-check.json').write_text(json.dumps({'originalReportHash': ff.digest(json.loads(original[0])),
            'originalSnapshotHash': ff.digest(json.loads(original[1])), 'storedBytesUnchanged': True,
            'amendmentCount': 2, 'updateRejected': True, 'deleteRejected': True}, indent=2), encoding='utf-8')


@pytest.mark.parametrize('fault', ['kickoff', 'started', 'identity', 'missing_report'])
def test_correction_requires_saved_matching_pregame_report(sandbox, monkeypatch, fault):
    if fault != 'missing_report':
        assert ff.generate(sandbox, 'final')
    changed = deepcopy(sandbox)
    if fault == 'kickoff':
        monkeypatch.setattr(ff, 'now', lambda: AT + timedelta(hours=1))
    if fault == 'started':
        monkeypatch.setattr(ff, 'current_row', lambda ident: {**sandbox, 'started': True})
    if fault == 'identity':
        changed['teams']['away']['id'] = 'wrong'
    with pytest.raises((ValueError, LookupError)):
        ff.record_baseline_amendment(changed, 'final', '核对统计首选')
    with ff.connect() as db:
        assert db.execute('SELECT count(*) FROM forecast_amendments').fetchone()[0] == 0
