import copy

import pytest

from football import evidence_reviews as reviews
from football import local_evidence_review


@pytest.fixture(autouse=True)
def legacy_generator_contract(monkeypatch):
    """Exercise the retained optional generator; production local routing is tested separately."""
    monkeypatch.setattr(local_evidence_review, 'generate', reviews._generate_analysis)


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
    def model(rules, context, tokens):
        value = copy.deepcopy(a)
        mapping = {old['id']: new['id'] for old, new in zip(d['facts'], context['facts'])}
        for section in ('claimAudits', 'drivers', 'lessons', 'marketReview'):
            for item in value[section]:
                item['evidenceIds'] = [mapping[e] for e in item['evidenceIds']]
        return value
    monkeypatch.setattr(reviews, 'request_json', model)
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


def test_correction_receives_all_semantic_errors_with_exact_locations(monkeypatch):
    d = dossier()
    calls = []

    def model(rules, context, tokens):
        calls.append(context)
        value = answer(context if len(calls) == 1 else context['dossier'])
        if len(calls) == 1:
            value['lessons'][0]['category'] = 'method'
            value['lessons'].append({**copy.deepcopy(value['lessons'][0]),
                                     'category': 'unresolved', 'evidenceIds': ['f1']})
            value['marketReview'] = [{'title': '无效来源', 'explanation': '待核对', 'evidenceIds': ['missing']}]
        return value

    monkeypatch.setattr(reviews, 'request_json', model)
    result = reviews._generate_analysis(d)
    assert len(calls) == 2
    errors = calls[1]['validationErrors']
    assert 'lessons 第1项：方法遗漏' in errors
    assert 'lessons 第2项：仅有赛果' in errors
    assert 'marketReview 第1项引用了不存在' in errors
    assert result['lessons'][0]['category'] == 'unexpected'
    assert result['lessons'][0]['evidenceIds'] == [d['facts'][1]['id']]


def test_hypothesis_cannot_be_labelled_as_observed_fact():
    d = dossier()
    a = answer(d)
    a['drivers'][0]['kind'] = 'observed'
    with pytest.raises(ValueError, match='inference'):
        reviews.validate_analysis(a, d)
    a['drivers'][0]['kind'] = 'inference'
    assert reviews.validate_analysis(a, d)['drivers'][0]['kind'] == 'inference'


def test_generator_downgrades_speculation_without_mutating_draft_or_losing_citations(monkeypatch):
    d = dossier()
    calls = []

    def reply(rules, context, tokens):
        value = answer(context)
        value['drivers'][0]['kind'] = 'observed'
        calls.append(value)
        return value

    monkeypatch.setattr(reviews, 'request_json', reply)
    result = reviews._generate_analysis(d)
    assert len(calls) == 1
    assert calls[0]['drivers'][0]['kind'] == 'observed'
    assert result['drivers'][0]['kind'] == 'inference'
    assert result['drivers'][0]['explanation'] == calls[0]['drivers'][0]['explanation']
    assert result['drivers'][0]['evidenceIds'] == [d['facts'][1]['id']]


def test_analysis_revision_creates_new_report_without_changing_original(tmp_path, monkeypatch):
    monkeypatch.setattr(reviews, 'STATE', tmp_path)
    d = dossier()
    monkeypatch.setattr(reviews, 'request_json', lambda rules, context, tokens: answer(context))
    first = reviews.build_review('football', 'fixture', d, True)
    monkeypatch.setattr(reviews, 'ANALYSIS_REVISION', 'new-audit-rules')
    second = reviews.build_review('football', 'fixture', d, True)
    assert first['revision'] != second['revision']
    assert first['dossier']['original'] == second['dossier']['original']
    assert len(list(tmp_path.glob('evidence-reviews/football/*/*.json'))) == 2


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
    calls = []
    def model(rules, context, tokens):
        calls.append(context)
        value = answer(context if len(calls) == 1 else context['dossier'])
        if len(calls) == 1:
            value['lessons'][0]['evidenceIds'] = []
        return value
    monkeypatch.setattr(reviews, 'request_json', model)
    result = reviews.build_review('football', 'fixture', d, True)
    assert result['analysisStatus'] == 'ready'
    assert len(calls) == 2 and calls[1]['validationErrors'][0]['loc'] == ('lessons', 0, 'evidenceIds')
    assert calls[1]['dossier']['original'] == d['original']
    assert calls[1]['dossier']['facts'][1]['id'] == 'f2'
    assert result['drivers'][0]['evidenceIds'] == [d['facts'][1]['id']]


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


def test_readable_model_references_restore_stable_citations_and_preserve_evidence(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(reviews, 'STATE', tmp_path)
    d = dossier()
    d['snapshot'] = {'privateInput': 'kept for audit'}
    d['timeline'] = [{'time': '20′', 'text': '伤退', 'evidenceIds': [d['facts'][1]['id']]}]
    original = copy.deepcopy(d)
    def model(rules, context, tokens):
        assert context['facts'][1]['id'] == 'f2'
        assert context['timeline'][0]['evidenceIds'] == ['f2']
        return answer(context)
    monkeypatch.setattr(reviews, 'request_json', model)
    result = reviews.build_review('football', 'fixture', d, True)
    assert d == original
    assert result['drivers'][0]['evidenceIds'] == [d['facts'][1]['id']]
    assert 'snapshot' not in result['dossier'] and 'evidenceSnapshot' not in result
    saved = json.loads(next(tmp_path.glob('evidence-reviews/football/*/*.json')).read_text('utf-8'))
    assert saved['evidenceSnapshot'] == original


def test_missing_claim_links_are_empty_but_never_prove_method_error():
    d = dossier()
    a = answer(d)
    a['lessons'][0].pop('claimIds')
    assert reviews.validate_analysis(a, d)['lessons'][0]['claimIds'] == []
    a['lessons'][0]['category'] = 'method'
    with pytest.raises(ValueError, match='原判断'):
        reviews.validate_analysis(a, d)
