import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from football import match_centre_research as centre, racing_pace as pace, match_research
from football.daily_scores import parse_event
from football.files import publish, read_json
from test_daily_research import fixture


class CentreTests(unittest.TestCase):
    def setUp(self):
        self.row = parse_event(fixture(), '2026-11-20', datetime.now(timezone.utc).isoformat(), {})
        self.match = {'id': 'espn:123', 'competition': '英超', 'date': '2026-11-20',
                      'kickoff': self.row['kickoff'], 'home': 'Home', 'away': 'Away'}

    def test_identity_rejects_different_leg_competition_and_swapped_sides(self):
        self.assertTrue(centre.same_fixture(self.row, self.match, 'epl'))
        for changed in ({'kickoff': '2026-11-21T18:00Z'}, {'id': 'espn:999'}, {'home': 'Away', 'away': 'Home'}):
            self.assertFalse(centre.same_fixture(self.row, {**self.match, **changed}, 'epl'))
        self.assertFalse(centre.same_fixture(self.row, self.match, 'ucl'))

    def test_summary_requires_competition_and_opponents(self):
        raw = {'header': fixture(), 'gameInfo': {'venue': {'fullName': 'Ground'}}}
        self.assertEqual(centre.summary_row(raw, self.match, 'epl', self.row['updatedAt'], {})['venue']['fullName'], 'Ground')
        raw['header']['uid'] = 's:600~l:775~e:123'
        with self.assertRaises(ValueError):
            centre.summary_row(raw, self.match, 'epl', self.row['updatedAt'], {})

    def test_paused_uses_saved_daily_row_without_network_or_snapshot_write(self):
        with patch.object(centre, 'match_catalogue', return_value=({'teams': []}, [self.match])), \
             patch.object(centre, 'identities', return_value=({}, {})), \
             patch.object(centre, 'read_control', return_value={'enabled': False}), \
             patch.object(centre, 'load', side_effect=lambda p: {'matches': [self.row]} if p.name == 'daily-football.json' else {}), \
             patch.object(centre, 'resolve_event') as resolve, patch.object(centre, 'cached_json') as fetch, \
             patch.object(centre, 'attach_research') as save:
            result = centre.get_research(self.match['id'], 'epl')
        self.assertTrue(result['paused'])
        self.assertEqual(result['match']['id'], '123')
        resolve.assert_not_called(); fetch.assert_not_called(); save.assert_not_called()

    def test_wrong_team_research_cache_is_not_reused_while_paused(self):
        old = {'eventId': '123', 'kickoff': self.row['kickoff'], 'updatedAt': self.row['updatedAt'],
               'teams': {'home': {'teamId': '1'}, 'away': {'teamId': 'wrong'}}}
        with patch.object(match_research, 'load', return_value=old), \
             patch.object(match_research, 'read_control', return_value={'enabled': False}), \
             patch.object(match_research, 'build') as build:
            result = match_research.research_row(self.row)
        self.assertNotIn('teams', result)
        build.assert_not_called()

    def test_local_history_fallback_keeps_identity_and_excludes_future_and_provisional(self):
        from football.local_match_history import local_history
        past = {**self.match, 'kickoff': '2026-11-10T12:00Z', 'homeGoals': 2, 'awayGoals': 1, 'finished': True}
        data = {'teams': [{'name': 'Home', 'espnId': '1'}, {'name': 'Away', 'espnId': '2'}],
                'matches': [past, {**past, 'kickoff': '2026-11-21T12:00Z'},
                            {**past, 'kickoff': '2026-11-15T12:00Z', 'provisional': True}]}
        with patch('football.local_match_history.LEAGUES', ['epl']):
            rows = local_history('1', datetime(2026, 11, 20, tzinfo=timezone.utc),
                                 lambda p: data if p.name == 'data.json' else {})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['opponentId'], '2')
        self.assertEqual(rows[0]['result'], 'W')

    def test_date_only_archives_are_available_but_never_from_current_day(self):
        from football.local_match_history import local_history
        past = {**self.match, 'id': 'archive', 'date': '2026-11-01', 'kickoff': None, 'homeGoals': 1, 'awayGoals': 1, 'finished': True}
        data = {'teams': [{'name': 'Home', 'espnId': '1'}, {'name': 'Away', 'espnId': '2'}],
                'matches': [past, {**past, 'id': 'today', 'date': '2026-11-20'}]}
        with patch('football.local_match_history.LEAGUES', ['epl']):
            rows = local_history('1', datetime(2026, 11, 20, 18, tzinfo=timezone.utc), lambda p: data if p.name == 'data.json' else {})
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]['dateOnly'])

    def test_failed_refresh_keeps_source_time_and_does_not_publish_fake_freshness(self):
        old = {'updatedAt': '2026-01-01T00:00:00Z', 'raw': {'header': {'id': '123'}}}
        with patch.object(match_research, 'load', return_value=old), \
             patch.object(match_research, 'fetch_json', side_effect=OSError('unavailable')), \
             patch.object(match_research, 'publish') as save:
            value = match_research.cached_json('https://example.test/source', Path('cache.json'), 60, datetime.now(timezone.utc))
        self.assertEqual(value['_cachedSourceAt'], old['updatedAt'])
        self.assertEqual(value['header']['id'], '123')
        save.assert_not_called()


class PaceTests(unittest.TestCase):
    def setUp(self):
        self.race = {'id': '2026-11-20-HV-1', 'date': '2026-11-20', 'offTime': '2026-11-20T12:00:00Z',
                     'courseName': '跑马地', 'track': '草地 C 赛道', 'distance': 1200, 'status': 'scheduled',
                     'entries': [{'id': 'A', 'name': '甲', 'number': '1', 'draw': '3'}]}
        self.record = {'date': '2026-11-10', 'raceId': '2026-11-10-HV-1', 'course': '跑马地', 'surface': '草地',
                       'distance': 1200, 'running': '1 2 3', 'place': 3, 'source': 'https://example.test/results'}

    def test_history_excludes_current_future_duplicates_and_invalid_results(self):
        records = [self.record, copy.deepcopy(self.record), {**self.record, 'date': '2026-11-21'},
                   {**self.record, 'date': self.race['date']}, {**self.record, 'raceId': 'bad', 'place': 2},
                   {**self.record, 'raceId': 'withdrawn', 'withdrawn': True},
                   {**self.record, 'raceId': 'older', 'date': '2026-11-01', 'running': '2 2 3', 'surface': '全天候跑道'}]
        result = pace.runner_profile(self.race['entries'][0], self.race, {'records': records})
        self.assertEqual(result['samples'], 2)
        self.assertTrue(result['evidence'][0]['similar'])
        self.assertFalse(result['evidence'][1]['similar'])
        self.assertEqual(result['style'], '放头')
        sparse = pace.runner_profile(self.race['entries'][0], self.race, {'records': [self.record]})
        self.assertIsNone(sparse['earlyPosition'])

    def test_snapshot_frozen_after_off_and_corrupt_history_not_called_pregame(self):
        now = datetime.now(timezone.utc)
        self.race['offTime'] = (now + timedelta(hours=1)).isoformat()
        with tempfile.TemporaryDirectory() as folder, patch.object(pace, 'STATE', Path(folder)), \
             patch.object(pace, 'FOLDER', Path(folder)), patch.object(pace, 'get_race', return_value=self.race), \
             patch.object(pace, 'read_control', return_value={'enabled': True}):
            before = pace.simulation(self.race['id'])
            self.assertTrue(before['hasPregame'])
            path = Path(folder) / 'racing-pace' / (self.race['id'] + '.json')
            raw = path.read_bytes()
            self.race.update(status='finished', resultOfficial=True)
            after = pace.simulation(self.race['id'])
            self.assertEqual(after['hash'], before['hash'])
            self.assertEqual(path.read_bytes(), raw)
            altered = read_json(path); altered['runners'][0]['style'] = '后追'; publish(path, altered)
            fallback = pace.simulation(self.race['id'])
            self.assertFalse(fallback['hasPregame'])
            self.assertEqual(fallback['status'], 'retrospective')
            self.assertEqual(fallback['review']['checked'], 0)

    def test_paused_never_publishes_and_review_excludes_withdrawn_and_unknown(self):
        self.race['offTime'] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        with patch.object(pace, 'get_race', return_value=self.race), patch.object(pace, 'load', return_value={}), \
             patch.object(pace, 'read_control', return_value={'enabled': False}), patch.object(pace, 'publish') as save:
            self.assertTrue(pace.simulation(self.race['id'])['paused'])
        save.assert_not_called()
        self.race.update(status='finished', resultOfficial=True)
        self.race['entries'][0].update(running='1 2 3', place=3, withdrawn=True)
        report = pace.review({'runners': [{'id': 'A', 'style': '放头', 'earlyPosition': 1}]}, self.race, True)
        self.assertEqual(report['checked'], 0)


if __name__ == '__main__':
    unittest.main()
