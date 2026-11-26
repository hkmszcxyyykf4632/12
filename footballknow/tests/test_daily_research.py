import copy
import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from football.daily_scores import parse_event, refresh_daily, preserve_pregame_quotes, fetch_day
from football.motivation import build_original, review_match, verify_original, digest, attach_research
from football.match_research import lineup, lineup_diff, game_of, history_rows, streak
from football.match_weather import parse_forecast, forecast
from football.commodity_history import technical


def fixture():
    return {'id': '123', 'uid': 's:600~l:700~e:123', 'date': '2026-11-20T18:00Z', 'season': {'year': 2026},
        'competitions': [{'date': '2026-11-20T18:00Z', 'altGameNote': 'English Premier League',
            'status': {'type': {'name': 'STATUS_SCHEDULED', 'state': 'pre'}, 'period': None},
            'competitors': [{'homeAway': side, 'team': {'id': ident, 'displayName': name}, 'form': form, 'score': '0'}
                           for side, ident, name, form in [('home', '1', 'Home', 'WWWWW'), ('away', '2', 'Away', None)]]}]}


class DailyResearchTests(unittest.TestCase):
    def test_daily_scores_use_the_working_shared_espn_client(self):
        from urllib.error import HTTPError
        from urllib.request import Request
        event = fixture()
        event['competitions'][0]['status']['type'] = {'name': 'STATUS_FULL_TIME', 'completed': True}
        event['competitions'][0]['competitors'][0]['score'] = '2'
        def source(request, **kwargs):
            # Observed on the live endpoint: the generic custom-agent request is rejected,
            # while the ESPN client already used by the league jobs returns the scoreboard.
            if isinstance(request, Request) and request.get_header('User-agent', '').startswith('FootballKnow/'):
                raise HTTPError(request.full_url, 403, 'Forbidden', {}, None)
            return io.BytesIO(json.dumps({'events': [event]}).encode())
        with patch('urllib.request.urlopen', side_effect=source):
            rows = fetch_day('2026-11-20', '2026-11-21T11:00:00+00:00', {})
        self.assertTrue(rows[0]['finished'])
        self.assertEqual(rows[0]['teams']['home']['goals'], 2)

    def test_pregame_quotes_survive_live_prices_and_check_match_identity(self):
        before = parse_event(fixture(), '2026-11-20', '2026-11-20T17:55:00+00:00', {})
        quote = {'market': 'asian-handicap', 'provider': 'Source', 'via': 'ESPN', 'phase': 'latest',
                 'line': -.5, 'prices': {'H': 1.9, 'A': 1.9}, 'fetchedAt': before['updatedAt'], 'inPlay': False}
        before['quotes'] = [{**quote, 'phase': 'opening', 'line': 0}, quote]
        stale = copy.deepcopy(before)
        stale['quotes'] = [{**quote, 'line': -2, 'fetchedAt': '2026-11-20T16:00:00+00:00'}]
        retained = preserve_pregame_quotes(stale, before)
        self.assertEqual(next(q['line'] for q in retained['quotes'] if q['phase'] == 'latest'), -.5)
        after = copy.deepcopy(before)
        after.update(started=True, finished=True, updatedAt='2026-11-20T20:00:00+00:00')
        after['quotes'] = [{**quote, 'line': -2, 'fetchedAt': after['updatedAt'], 'inPlay': True}]
        saved = preserve_pregame_quotes(after, before)
        last = next(q for q in saved['quotes'] if q.get('lastPregame'))
        self.assertEqual(last['line'], -.5)
        self.assertEqual(last['fetchedAt'], before['updatedAt'])
        self.assertFalse(last['inPlay'])
        self.assertEqual(len(saved['quotes']), 3)
        again = copy.deepcopy(after)
        again['quotes'] = [{**quote, 'line': -3, 'fetchedAt': after['updatedAt'], 'inPlay': True}]
        self.assertEqual(len(preserve_pregame_quotes(again, saved)['quotes']), 3)
        changed = copy.deepcopy(again)
        changed['teams']['away']['id'] = '99'
        changed['quotes'] = []
        self.assertEqual(preserve_pregame_quotes(changed, before)['quotes'], [])

    def test_scheduled_placeholder_scores_and_after_kickoff(self):
        row = parse_event(fixture(), '2026-11-20', '2026-11-20T10:00:00+00:00', {})
        self.assertIsNone(row['teams']['home']['goals'])
        at = datetime(2026, 11, 20, 10, tzinfo=timezone.utc)
        original = build_original(row, {}, at)
        self.assertTrue(verify_original(original, row))
        row.update(started=True, finished=True, state='finished')
        row['teams']['home']['goals'], row['teams']['away']['goals'] = 1, 0
        self.assertEqual(review_match(row, original)['status'], '已复核')
        self.assertIsNone(build_original(row, {}, at))
        original['teams']['home']['tendency'] = '改写'
        self.assertFalse(verify_original(original, row))

    def test_unavailable_odds_do_not_drop_a_match(self):
        event = fixture()
        event['competitions'][0]['odds'] = [None, {'provider': None}, {'provider': {'name': 'Source'}, 'pointSpread': {'home': None}}]
        row = parse_event(event, '2026-11-20', '2026-11-20T10:00:00+00:00', {})
        self.assertEqual(row['quotes'], [])
        self.assertEqual(row['id'], '123')

    def test_source_failure_preserves_rows(self):
        at = datetime(2026, 11, 20, 10, tzinfo=timezone.utc)
        row = parse_event(fixture(), '2026-11-20', at.isoformat(), {})
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'daily.json'
            from football.files import publish, read_json
            publish(output, {'matches': [row], 'updatedAt': at.isoformat()})
            def fail(*args):
                raise OSError('source unavailable')
            with patch('football.daily_scores.OUTPUT', output), patch('football.daily_scores.STATE', Path(folder)), patch('football.daily_scores.identities', return_value=({}, {})):
                with self.assertRaises(OSError):
                    refresh_daily(at, fail)
            self.assertEqual(read_json(output)['matches'][0]['id'], '123')
            self.assertEqual(len(read_json(output)['errors']), 8)

    def test_future_source_failure_does_not_delay_live_scores(self):
        at = datetime(2026, 11, 20, 10, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'daily.json'
            def source(day, *args):
                if day > '2026-11-21':
                    raise OSError('future date unavailable')
                return []
            with patch('football.daily_scores.OUTPUT', output), patch('football.daily_scores.STATE', Path(folder)), patch('football.daily_scores.identities', return_value=({}, {})):
                result = refresh_daily(at, source)
            self.assertEqual(len(result['errors']), 4)
            self.assertEqual(result['updatedAt'], at.isoformat())

    def test_only_eleven_unique_confirmed_players(self):
        roster = {'team': {'id': '1'}, 'formation': '4-3-3', 'roster': [{'starter': True, 'athlete': {'id': str(i), 'displayName': str(i)}} for i in range(11)]}
        raw = {'rosters': [roster]}
        original = lineup(raw, '1')
        self.assertTrue(original['confirmed'])
        changed = copy.deepcopy(raw)
        changed['rosters'][0]['roster'][0]['athlete']['id'] = '20'
        difference = lineup_diff(lineup(changed, '1'), original)
        self.assertEqual(difference['retained'], 10)
        changed['rosters'][0]['roster'][0]['athlete']['id'] = '1'
        self.assertFalse(lineup(changed, '1')['confirmed'])

    def test_summary_identity_rejects_wrong_opponent(self):
        row = parse_event(fixture(), '2026-11-20', '2026-11-20T10:00:00+00:00', {})
        raw = {'header': {'id': '123', 'competitions': fixture()['competitions']}}
        self.assertEqual(game_of(raw, '123', row)['date'], row['kickoff'].replace(':00+00:00', 'Z'))
        raw['header']['competitions'][0]['competitors'][1]['team']['id'] = '3'
        with self.assertRaises(ValueError):
            game_of(raw, '123', row)

    def test_weather_period_and_no_hindsight(self):
        at = datetime(2026, 11, 20, 18, tzinfo=timezone.utc)
        raw = {'properties': {'timeseries': [{'time': at.isoformat(), 'data': {'instant': {'details': {'air_temperature': 30, 'wind_speed': 9}}, 'next_6_hours': {'details': {'precipitation_amount': 4}}}}]}}
        result = parse_forecast(raw, at, {'name': 'London'}, '2026-11-20T10:00:00+00:00')
        self.assertEqual(result['precipitationHours'], 6)
        self.assertEqual(result['precipitation'], 4)
        with patch('football.match_weather.urlopen') as request:
            self.assertIn('已开始', forecast({}, at, at)['status'])
            request.assert_not_called()

    def test_technical_analysis_is_calculated(self):
        rows = [{'date': f'2026-10-{i:02}', 'close': 100+i} for i in range(1, 31)]
        result = technical(rows)
        self.assertEqual(result['ma5'], 128)
        self.assertEqual(result['trend'], '短期偏强')
        self.assertGreater(result['volatility20Annualized'], 0)

    def test_weather_cache_respects_three_hour_interval(self):
        at = datetime(2026, 11, 20, 10, tzinfo=timezone.utc)
        kickoff = at + timedelta(days=1)
        raw = {'properties': {'timeseries': [{'time': kickoff.isoformat(), 'data': {'instant': {'details': {'air_temperature': 12}}}}]}}
        def response(*args, **kwargs):
            result = io.BytesIO(json.dumps(raw).encode())
            result.headers = {}
            return result
        location = {'id': 600, 'name': 'London', 'latitude': 51.5, 'longitude': -.1}
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ', {'FOOTBALL_MET_TERMS_ACCEPTED': '1'}), patch('football.match_weather.STATE', Path(folder)), patch('football.match_weather.locate', return_value=location), patch('football.match_weather.urlopen', side_effect=response) as request:
            self.assertEqual(forecast({}, kickoff, at)['status'], 'available')
            self.assertEqual(forecast({}, kickoff, at + timedelta(hours=2))['status'], 'available')
            self.assertEqual(request.call_count, 1)
            forecast({}, kickoff, at + timedelta(hours=3))
            self.assertEqual(request.call_count, 2)

    def test_lineup_retains_verified_chinese_variants(self):
        roster = {'team': {'id': '1'}, 'roster': [{'starter': True, 'athlete': {'id': str(i), 'displayName': 'Player ' + str(i)}} for i in range(11)]}
        result = lineup({'rosters': [roster]}, '1', {'player0': {'mandarin': '中文译名', 'cantonese': '粵語譯名'}})
        self.assertTrue(result['confirmed'])
        self.assertEqual(result['players'][0]['mandarin'], '中文译名')
        self.assertEqual(result['players'][0]['cantonese'], '粵語譯名')
        self.assertNotIn('mandarin', result['players'][1])


class ObjectiveMatchContextTests(unittest.TestCase):
    def test_rank_and_form_do_not_create_mindset_labels(self):
        at = datetime(2026, 11, 20, 10, tzinfo=timezone.utc)
        row = parse_event(fixture(), '2026-11-20', at.isoformat(), {})
        row['teams']['away']['form'] = 'LLLLL'
        context = {'table': {'updatedAt': at.isoformat(), 'season': str(row['season']), 'source': 'https://example.test/table', 'entries': [
            {'espnId': '1', 'rank': 2, 'points': 24, 'played': 10},
            {'espnId': '2', 'rank': 12, 'points': 12, 'played': 10}]}}
        original = build_original(row, context, at)
        self.assertEqual(original['version'], 'match-context-2')
        for team in original['teams'].values():
            self.assertNotIn('tendency', team)
            self.assertNotIn('drawAcceptance', team)
            self.assertEqual(team['checks'], [])
            self.assertIn('若比分落后', team['scenarios'][0])
        self.assertIn('第2、24分', original['teams']['home']['summary'])
        self.assertIn('0胜、0平、5负', original['teams']['away']['summary'])
        self.assertIn('取胜后为27分', str(original['teams']['home']['evidence']))

    def test_old_snapshot_is_not_rewritten_and_result_does_not_grade_intent(self):
        at = datetime(2026, 11, 20, 10, tzinfo=timezone.utc)
        row = parse_event(fixture(), '2026-11-20', at.isoformat(), {})
        original = build_original(row, {}, at)
        original['version'] = 'intent-rules-1'
        for team in original['teams'].values():
            team.update(tendency='保平倾向', checks=[{'id': 'result', 'label': '全场不败', 'rule': 'unbeaten'}])
        original['hash'] = digest({k: v for k, v in original.items() if k != 'hash'})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '123.json'
            path.write_text(json.dumps(original), encoding='utf-8')
            before = path.read_bytes()
            attach_research(row, [], {}, at, Path(folder))
            self.assertEqual(path.read_bytes(), before)
        row.update(finished=True, scoreScope='90分钟含补时')
        row['teams']['home'].update(goals=2, shots=16)
        row['teams']['away'].update(goals=1, shots=4)
        review = review_match(row, original)
        self.assertEqual(review['teams']['home']['checks'], [])
        self.assertNotIn('supported', review['teams']['home'])
        self.assertIn('2 : 1', review['teams']['home']['summary'])
        self.assertIn('16 : 4', review['teams']['home']['summary'])
        self.assertTrue(verify_original(original, row))
