import copy

import pytest

from football import evidence_reviews as reviews


def dossier():
    d = reviews.new_dossier('football', 'fixture', {'summary': ['主队锋线齐整，能够持续施压。'], 'issuedAt': '2026-11-20T10:00:00+00:00'})
    s = reviews.add_source(d, 'https://example.org/report', '正式战报', '2026-11-21T01:00:00+00:00')
    reviews.add_fact(d, '双方1:1完场。', [s], category='result')
    reviews.add_fact(d, '第20分钟首发中锋因伤被换下。', [s], category='injury', time='20′', before_event=False)
    return d


def answer(d):
    return {'summary': ['锋线完整的原假设在比赛中发生变化。'],
            'claimAudits': [{'claimId': d['claims'][0]['id'], 'verdict': 'contradicted',
                             'explanation': '中锋提前离场，不能继续沿用全场锋线完整的假设。', 'evidenceIds': [d['facts'][1]['id']]}],
            'drivers': [{'title': '中锋伤退', 'kind': 'inference', 'explanation': '伤退可能限制进攻延续性，不能据此证明没有伤退就一定获胜。', 'evidenceIds': [d['facts'][1]['id']]}],
            'lessons': [{'title': '临场伤退', 'category': 'unexpected', 'explanation': '发生于开赛后，不可倒写成赛前已经知道。',
                         'claimIds': [d['claims'][0]['id']], 'evidenceIds': [d['facts'][1]['id']], 'nextCheck': '下一场核对替补中锋和无中锋时的阵容调整。'}],
            'marketReview': []}


def test_score_only_never_generates_a_tactical_cause(tmp_path, monkeypatch):
    monkeypatch.setattr(reviews, 'STATE', tmp_path)
    d = dossier()
    d['facts'] = d['facts'][:1]
    monkeypatch.setattr(reviews, 'request_json', lambda *a: pytest.fail('Score alone must not generate causal explanations'))
    r = reviews.build_review('football', 'fixture', d, True)
    assert r['analysisStatus'] == 'limited'
    assert r['drivers'] == [] and r['lessons'] == []


def test_claim_audit_rejects_invented_sources_and_unexamined_original():
    d = dossier()
    a = answer(d)
    a['drivers'][0]['evidenceIds'] = ['made-up']
    with pytest.raises(ValueError):
        reviews.validate_analysis(a, d)
    a = answer(d)
    a['claimAudits'] = []
    with pytest.raises(ValueError):
        reviews.validate_analysis(a, d)


def test_new_evidence_creates_separate_revision_without_rewriting_original(tmp_path, monkeypatch):
    monkeypatch.setattr(reviews, 'STATE', tmp_path)
    d = dossier()
    original = copy.deepcopy(d['original'])
    calls = []
    def reply(rules, context, tokens):
        calls.append(context)
        return answer(context)
    monkeypatch.setattr(reviews, 'request_json', reply)
    first = reviews.build_review('football', 'fixture', d, True)
    d['sources'][0]['updatedAt'] = '2026-11-21T02:00:00+00:00'
    assert reviews.build_review('football', 'fixture', d, True)['revision'] == first['revision']
    reviews.add_fact(d, '官方射正统计为4:5。', [d['sources'][0]['id']], category='statistics')
    second = reviews.build_review('football', 'fixture', d, True)
    assert first['revision'] != second['revision']
    assert len(calls) == 2 and d['original'] == original
    assert len(list(tmp_path.glob('evidence-reviews/football/*/*.json'))) == 2


def test_review_lessons_do_not_leak_into_earlier_predictions(tmp_path, monkeypatch):
    monkeypatch.setattr(reviews, 'STATE', tmp_path)
    d = dossier()
    a = answer(d)
    a['lessons'][0]['category'] = 'method'
    known = reviews.add_fact(d, '赛前已经记录对手近五场多次反击进球。', [d['sources'][0]['id']], before_event=True)
    a['lessons'][0]['evidenceIds'].append(known)
    monkeypatch.setattr(reviews, 'request_json', lambda *args: a)
    reviews.build_review('football', 'fixture', d, True)
    assert reviews.method_memory('football', '2020-01-01T00:00:00+00:00') == []
    future = reviews.method_memory('football', '2100-01-01T00:00:00+00:00')
    assert future and future[0]['validation'] == '待后续样本检验'


def test_post_event_injury_alone_cannot_prove_a_pregame_omission():
    d = dossier()
    a = answer(d)
    a['lessons'][0]['category'] = 'method'
    with pytest.raises(ValueError, match='赛前已知'):
        reviews.validate_analysis(a, d)


def test_revision_file_is_complete_before_becoming_visible(tmp_path, monkeypatch):
    path = tmp_path / 'revision.json'
    link = reviews.os.link
    def inspect_before_link(source, destination):
        assert not destination.exists()
        import json
        assert json.loads(open(source, encoding='utf-8').read()) == {'value': 1}
        link(source, destination)
    monkeypatch.setattr(reviews.os, 'link', inspect_before_link)
    assert reviews._save_revision(path, {'value': 1}) == {'value': 1}
    monkeypatch.setattr(reviews.os, 'link', link)
    assert reviews._save_revision(path, {'value': 2}) == {'value': 1}


def test_uncited_lesson_gets_one_correction_before_publication(tmp_path, monkeypatch):
    monkeypatch.setattr(reviews, 'STATE', tmp_path)
    d = dossier()
    invalid = answer(d)
    invalid['lessons'][0]['evidenceIds'] = []
    calls = []
    def model(rules, context, tokens):
        calls.append(context)
        return invalid if len(calls) == 1 else answer(d)
    monkeypatch.setattr(reviews, 'request_json', model)
    result = reviews.build_review('football', 'fixture', d, True)
    assert result['analysisStatus'] == 'ready'
    assert len(calls) == 2 and calls[1]['validationErrors'][0]['loc'] == ('lessons', 0, 'evidenceIds')
    assert calls[1]['dossier'] == d


def test_failed_correction_is_never_published(tmp_path, monkeypatch):
    monkeypatch.setattr(reviews, 'STATE', tmp_path)
    d = dossier()
    invalid = answer(d)
    invalid['drivers'][0]['evidenceIds'] = ['invented']
    calls = []
    monkeypatch.setattr(reviews, 'request_json', lambda *args: calls.append(args) or invalid)
    with pytest.raises(ValueError, match='不存在'):
        reviews.build_review('football', 'fixture', d, True)
    assert len(calls) == 2
    assert not list(tmp_path.glob('evidence-reviews/football/*/*.json'))
