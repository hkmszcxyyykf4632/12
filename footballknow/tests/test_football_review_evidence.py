import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from football import football_review_evidence as module
from football.evidence_reviews import validate_analysis


class FootballDossierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.patch = patch.object(module, 'PUBLIC', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.match = {'id': 'espn:123', 'home': 'Alpha', 'away': 'Beta', 'date': '2026-11-01',
                      'kickoff': '2026-11-01T15:00:00Z', 'homeGoals': 1, 'awayGoals': 0,
                      'finished': True, 'source': 'https://example.test/result'}
        self.detail = {'matchId': 'espn:123', 'league': 'epl', 'date': '2026-11-01',
                       'home': 'Alpha', 'away': 'Beta', 'completed': True,
                       'source': 'https://example.test/lineup', 'updatedAt': '2026-11-01T18:00:00Z',
                       'events': [{'type': 'goal', 'label': '进球', 'side': 'home', 'clock': "45+2'",
                                   'players': [{'name': 'Scorer'}]}],
                       'statistics': [{'side': 'home', 'values': {'shots': '8'}}]}

    def build(self, detail=None):
        return module.build_dossier(self.match, {'prediction': '原始观点'}, detail=detail)

    def texts(self, dossier):
        return '\n'.join(f['text'] for f in dossier['facts'])

    def test_no_detail_does_not_assert_tactics(self):
        result = self.build()
        self.assertEqual(result['original'], {'prediction': '原始观点'})
        self.assertEqual(len(result['facts']), 1)
        self.assertEqual(result['facts'][0]['category'], 'result')
        self.assertEqual(result['timeline'], [])
        self.assertTrue(any('详情' in s for s in result['gaps']))
        self.assertEqual(result['identity'], 'epl:espn:123')
        self.assertEqual(result['fixture']['kickoff'], self.match['kickoff'])

    def test_detail_refresh_does_not_retimestamp_facts(self):
        first = self.build(self.detail)
        self.detail['updatedAt'] = '2026-11-02T19:00:00Z'
        second = self.build(self.detail)
        self.assertEqual(first['facts'], second['facts'])

    def test_wrong_identity_date_live_and_score_are_rejected(self):
        for field, value in [('home', 'Gamma'), ('away', 'Gamma'), ('date', '2026-11-02'),
                             ('matchId', 'espn:456'), ('league', 'ucl'), ('completed', False),
                             ('kickoff', '2026-11-01T16:00:00Z'), ('homeGoals', 2)]:
            with self.subTest(field=field):
                detail = {**self.detail, field: value}
                result = self.build(detail)
                self.assertEqual(result['timeline'], [])
                self.assertNotIn('射门', self.texts(result))

    def test_goals_reconcile_or_are_withheld(self):
        good = self.build(self.detail)
        self.assertEqual(len(good['timeline']), 1)
        self.assertIn('1–0', good['timeline'][0]['text'])
        self.assertIn('射门 8', self.texts(good))
        bad = copy.deepcopy(self.detail)
        bad['events'].append(dict(bad['events'][0], clock="60'"))
        result = self.build(bad)
        self.assertEqual(result['timeline'], [])
        self.assertTrue(any('对账' in s for s in result['gaps']))

    def test_own_goal_needs_scoring_side(self):
        self.detail['events'][0]['type'] = 'own-goal'
        self.assertEqual(self.build(self.detail)['timeline'], [])
        self.detail['events'][0]['scoringSide'] = 'home'
        self.assertEqual(len(self.build(self.detail)['timeline']), 1)

    def test_roster_substitution_does_not_invent_intent_or_red_card_substitution(self):
        self.detail['lineups'] = {'home': {'name': 'Alpha', 'players': [
            {'espnId': '1', 'name': 'Off', 'left': "60'", 'redCards': 1},
            {'espnId': '2', 'name': 'On', 'entered': "60'", 'replaces': '1'}]}}
        text = self.texts(self.build(self.detail))
        self.assertIn('On换入', text)
        self.assertIn('Off红牌离场', text)
        self.assertNotIn('Off换出', text)
        self.assertNotIn('教练决定', text)

    def test_verified_red_card_allows_timed_unexpected_lesson(self):
        self.detail['events'].append({'type': 'red-card', 'label': '红牌', 'side': 'away',
                                      'clock': "60'", 'players': [{'name': 'Defender'}]})
        self.detail['lineups'] = {'home': {'name': 'Alpha', 'confirmed': True, 'players': [
            {'name': f'Starter{i}', 'starter': True, 'espnId': str(i)} for i in range(11)] + [
            {'name': 'Replacement', 'entered': "70'", 'espnId': '12'}]}}
        dossier = self.build(self.detail)
        red = next(f for f in dossier['facts'] if 'Defender' in f['text'])
        self.assertIs(red['beforeEvent'], False)
        self.assertEqual(red['time'], "60'")
        self.assertTrue(all(f['beforeEvent'] is False for f in dossier['facts'] if f['category'] == 'statistics'))
        starter = next(f for f in dossier['facts'] if f['category'] == 'lineup')
        self.assertIsNone(starter['beforeEvent'])
        sub = next(f for f in dossier['facts'] if 'Replacement换入' in f['text'])
        self.assertIs(sub['beforeEvent'], False)
        content = {'summary': ['已核实第60分钟红牌；影响程度仍待验证。'], 'claimAudits': [], 'drivers': [],
                   'marketReview': [], 'lessons': [{'title': '比赛内红牌', 'category': 'unexpected',
                   'explanation': '红牌发生在开赛后；不能由最终输赢证明其因果作用或赛前不可预见。',
                   'claimIds': [], 'evidenceIds': [red['id']], 'nextCheck': '核对红牌前后机会质量与人员变化。'}]}
        self.assertEqual(validate_analysis(content, dossier)['lessons'][0]['category'], 'unexpected')

    def quote(self, stamp='2026-11-01T13:00:00Z', **kw):
        return {'provider': 'Book', 'market': 'asian-handicap', 'via': 'ESPN', 'phase': 'latest',
                'fetchedAt': stamp, 'source': 'https://example.test/odds', 'line': -0.5,
                'prices': {'H': 1.9, 'A': 2.0}, **kw}

    def test_odds_line_price_and_margin_are_distinct(self):
        self.match['quotes'] = [self.quote(), self.quote('2026-11-01T14:00:00Z', prices={'H': 1.8, 'A': 2.1}),
                                self.quote('2026-11-01T14:30:00Z', line=-0.75)]
        text = self.texts(self.build())
        self.assertIn('主队 1.9→1.8', text)
        self.assertIn('盘口线变动 -0.5→-0.75', text)
        self.assertIn('隐含概率合计超额', text)
        self.assertIn('负数为主让', text)

    def test_invalid_or_postkickoff_odds_never_enter_facts(self):
        self.match['quotes'] = [self.quote('2026-11-01T15:00:00Z'), self.quote('bad'),
                                self.quote('2026-11-01T13:00:00'), self.quote(inPlay=True),
                                self.quote(prices={'H': '1.9', 'A': 2}), self.quote(line=True),
                                self.quote(matchId='espn:999'), self.quote(scope='first-half'),
                                self.quote(prices={'H': float('nan'), 'A': 2})]
        self.match['quotes'].append(self.quote(prices=None))
        self.assertEqual(len(self.build()['facts']), 1)

    def test_histories_do_not_mix_fixtures_or_providers(self):
        (self.root / 'market-odds.json').write_text(json.dumps({'league': 'epl', 'history': {
            'espn:123': [self.quote(), self.quote('2026-11-01T14:00:00Z', provider='Other')],
            'espn:999': [self.quote('2026-11-01T14:30:00Z', line=-2)]}}), encoding='utf-8')
        text = self.texts(self.build())
        self.assertNotIn('价格变化', text)
        self.assertNotIn('盘口线变动', text)
        self.assertNotIn('盘口 -2', text)

    def test_snapshot_quote_stays_original_and_retrospective_prices_are_not_pregame(self):
        snapshot = {'quotes': [self.quote(prices={'H': 2.5, 'A': 1.5})]}
        before = copy.deepcopy(snapshot)
        self.match['quotes'] = [self.quote('2026-11-02T13:00:00Z', phase='opening'), self.quote()]
        result = module.build_dossier(self.match, {'prediction': '原始观点'}, snapshot=snapshot)
        self.assertEqual(snapshot, before)
        self.assertEqual(result['snapshot'], before)
        self.assertNotIn('来源标记开盘', self.texts(result))
        self.assertIn('1.9', self.texts(result))

    def test_ligue1_daily_identity_and_source_do_not_become_epl(self):
        self.match.pop('source')
        self.match['competitionId'] = '710'
        result = module.build_dossier(self.match, None, league='ligue1')
        self.assertEqual(result['identity'], 'ligue1:espn:123')
        self.assertEqual(result['fixture']['league'], 'ligue1')
        self.assertEqual(result['sources'][0]['url'], '/daily-football.json')

    def test_original_adopted_quote_is_immutable_attributed_and_not_replaced(self):
        original = {'issuedAt': '2026-11-01T13:05:00Z', 'quote': self.quote(prices={'H': 2.5, 'A': 1.5})}
        before = copy.deepcopy(original)
        self.match['quotes'] = [self.quote('2026-11-01T14:00:00Z')]
        result = module.build_dossier(self.match, original)
        self.assertEqual(original, before)
        self.assertEqual(result['originalQuote'], before['quote'])
        adopted = next(f for f in result['facts'] if '原预测采用报价' in f['text'])
        self.assertIn('主队 2.5', adopted['text'])
        self.assertEqual(adopted['time'], '2026-11-01T13:00:00Z')
        self.assertTrue(adopted['beforeEvent'])
        src = next(s for s in result['sources'] if s['id'] in adopted['sourceIds'])
        self.assertEqual(src['updatedAt'], before['quote']['fetchedAt'])
        self.assertIn('主队 1.9', self.texts(result))

    def test_late_adopted_quote_is_record_not_verified_pregame(self):
        original = {'issuedAt': '2026-11-01T13:05:00Z', 'quote': self.quote('2026-11-01T16:00:00Z')}
        result = module.build_dossier(self.match, original)
        adopted = next(f for f in result['facts'] if '原预测采用报价' in f['text'])
        self.assertFalse(adopted['beforeEvent'])
        self.assertIn('不能完整证明', adopted['text'])

    def pregame_snapshot(self):
        return {'capturedAt': '2026-11-01T13:10:00Z', 'match': {
            'id': '123', 'league': 'epl', 'kickoff': self.match['kickoff'], 'started': False, 'finished': False,
            'teams': {'home': {'id': '10', 'name': 'Alpha'}, 'away': {'id': '20', 'name': 'Beta'}}},
            'research': {'eventId': '123', 'kickoff': self.match['kickoff'],
                'updatedAt': '2026-11-01T13:00:00Z', 'pregame': {'capturedAt': '2026-11-01T13:00:00Z'},
                'source': 'https://example.test/lineups', 'teams': {
                    'home': {'teamId': '10', 'lineup': {'confirmed': True, 'formation': '4-4-2', 'players': [
                        {'id': str(i), 'name': f'Player{i}'} for i in range(11)]}, 'form': {'summary': 'Invented dominance',
                        'matches': [{'date': '2026-10-20T15:00:00Z', 'opponent': 'Gamma', 'opponentId': '30',
                            'homeAway': 'away', 'goalsFor': 2, 'goalsAgainst': 1, 'source': 'https://example.test/prior'}]}},
                    'away': {'teamId': '20'}},
                'weather': {'status': 'available', 'source': 'https://example.test/weather',
                    'fetchedAt': '2026-11-01T12:00:00Z', 'forecastFor': self.match['kickoff'], 'temperature': 30,
                    'notes': ['Invented injury cause']}}}

    def signed_original(self, snapshot):
        return {'issuedAt': '2026-11-01T13:15:00Z', 'summary': ['预计主队在正常阵容下占优。'],
                'snapshotHash': hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                                                         separators=(',', ':')).encode()).hexdigest()}

    def test_saved_research_supplies_only_attributed_pregame_inputs_and_method_audit(self):
        snapshot = self.pregame_snapshot()
        original = self.signed_original(snapshot)
        unchanged = copy.deepcopy(snapshot)
        dossier = module.build_dossier(self.match, original, snapshot=snapshot)
        inputs = [f for f in dossier['facts'] if f['beforeEvent'] is True]
        self.assertEqual(len(inputs), 3)
        self.assertEqual(snapshot, unchanged)
        self.assertNotIn('Invented', self.texts(dossier))
        weather = next(f for f in inputs if '气温 30' in f['text'])
        content = {'summary': ['检查原判断是否充分使用天气输入。'], 'claimAudits': [
            {'claimId': 'c1', 'verdict': 'unresolved', 'explanation': '仍需后续样本。', 'evidenceIds': []}],
            'drivers': [], 'marketReview': [], 'lessons': [{'title': '天气检查项', 'category': 'method',
            'explanation': '赛前已有天气预报；是否遗漏仍需对照原判断，不推定因果。', 'claimIds': ['c1'],
            'evidenceIds': [weather['id']], 'nextCheck': '复核下一场预报与体能假设。'}]}
        self.assertEqual(validate_analysis(content, dossier)['lessons'][0]['category'], 'method')

    def test_snapshot_identity_timing_hash_and_stale_research_rejected(self):
        edits = [lambda s: s['research'].update(eventId='999'),
                 lambda s: s['research']['teams']['home'].update(teamId='999'),
                 lambda s: s['match']['teams']['home'].update(name='Wrong'),
                 lambda s: s['match'].update(league='ucl'),
                 lambda s: s['match'].update(started=True),
                 lambda s: s['research'].update(kickoff='2026-11-02T15:00:00Z'),
                 lambda s: s['research']['pregame'].update(capturedAt='2026-11-01T14:00:00Z'),
                 lambda s: s['research'].update(updatedAt='2026-11-01T16:00:00Z'),
                 lambda s: s['research'].update(message='cached source')]
        for edit in edits:
            snapshot = self.pregame_snapshot()
            edit(snapshot)
            result = module.build_dossier(self.match, self.signed_original(snapshot), snapshot=snapshot)
            self.assertFalse(any(f['beforeEvent'] is True for f in result['facts']))
        snapshot = self.pregame_snapshot()
        original = self.signed_original(snapshot)
        snapshot['research']['weather']['temperature'] = 99
        self.assertFalse(any(f['beforeEvent'] is True for f in module.build_dossier(self.match, original, snapshot=snapshot)['facts']))
        original = self.signed_original(snapshot)
        original['issuedAt'] = '2026-11-01T15:00:00Z'
        self.assertFalse(any(f['beforeEvent'] is True for f in module.build_dossier(self.match, original, snapshot=snapshot)['facts']))

    def test_snapshot_missing_sources_future_history_and_incomplete_lineup_are_not_facts(self):
        snapshot = self.pregame_snapshot()
        research = snapshot['research']
        research['teams']['home']['lineup']['players'].pop()
        research['teams']['home']['form']['matches'][0]['date'] = '2026-11-01T14:00:00Z'
        research['weather'].pop('source')
        result = module.build_dossier(self.match, self.signed_original(snapshot), snapshot=snapshot)
        self.assertFalse(any(f['beforeEvent'] is True for f in result['facts']))
        self.assertTrue(any('没有完整首发' in gap for gap in result['gaps']))

    def test_snapshot_history_is_bounded_and_source_not_summary(self):
        snapshot = self.pregame_snapshot()
        rows = snapshot['research']['teams']['home']['form']['matches']
        rows[:] = [{**rows[0], 'opponent': f'Club{i}', 'opponentId': str(100 + i)} for i in range(30)]
        result = module.build_dossier(self.match, self.signed_original(snapshot), snapshot=snapshot)
        self.assertEqual(sum('历史样本' in f['text'] for f in result['facts']), 10)

    def test_daily_fixture_normalizes_and_live_never_gets_event_facts(self):
        self.match['teams'] = {s: {'name': self.match.pop(s), 'goals': self.match.pop(s + 'Goals')} for s in ('home', 'away')}
        self.assertIn('1–0', self.texts(self.build(self.detail)))
        self.match['finished'] = False
        self.assertEqual(self.build(self.detail)['facts'], [])

    def test_curated_case_requires_exact_fixture_and_references(self):
        folder = self.root / 'review-evidence'
        folder.mkdir()
        case = {'identity': module._identity(self.match, 'epl'),
                'sources': [{'id': 's1', 'url': 'https://example.test/interview', 'title': 'Interview'}],
                'facts': [{'text': 'Exact interview', 'sourceIds': ['s1']},
                          {'text': 'No source', 'sourceIds': ['missing']}]}
        path = folder / 'football.json'
        path.write_text(json.dumps({'cases': [case]}), encoding='utf-8')
        self.assertIn('Exact interview', self.texts(self.build()))
        self.assertNotIn('No source', self.texts(self.build()))
        case['identity']['kickoff'] = '2026-11-01T16:00:00Z'
        path.write_text(json.dumps({'cases': [case]}), encoding='utf-8')
        self.assertNotIn('Exact interview', self.texts(self.build()))


if __name__ == '__main__':
    unittest.main()
