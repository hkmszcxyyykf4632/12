import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from football import coach_lineups as coaches


class CoachLineupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patcher = patch.object(coaches, 'PUBLIC', self.root)
        self.patcher.start()
        coaches._cache.clear()
        self.write('data.json', {'teams': [{'id': 1, 'name': 'Arsenal'}]})
        self.write('names.json', {'names': {'100': {'mandarin': '甲球员'}}})
        self.detail = {'league': 'epl', 'matchId': 'a', 'eventId': '12', 'date': '2026-11-01',
                       'home': 'Arsenal', 'away': 'Other', 'source': 'https://example.com/lineups/12',
                       'lineups': {'home': {'name': 'Arsenal', 'confirmed': True, 'formation': '4-3-3',
                                  'players': [{'espnId': str(i), 'playerCode': 100+i, 'name': f'Player {i}', 'starter': True} for i in range(11)]}}}

    def tearDown(self):
        self.patcher.stop()
        coaches._cache.clear()
        self.temp.cleanup()

    def write(self, name, value):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value), encoding='utf-8')

    def test_compact_confirmed_eleven_retains_identity_and_attribution(self):
        self.write('match-details/a.json', self.detail)
        result = coaches.coach_lineups('epl', 1)
        self.assertEqual(len(result['matches']), 1)
        row = result['matches'][0]
        self.assertEqual(row['starters'][0]['name'], '甲球员')
        self.assertEqual(row['starters'][0]['id'], '0')
        self.assertEqual(row['source'], self.detail['source'])
        self.assertEqual(row['formation'], '4-3-3')
        with self.assertRaises(LookupError):
            coaches.coach_lineups('epl', 99)

    def test_rejects_incomplete_duplicate_unconfirmed_and_wrong_team_lists(self):
        for variant in ['incomplete', 'duplicate', 'unconfirmed', 'wrong-team', 'wrong-league']:
            with self.subTest(variant=variant):
                d = json.loads(json.dumps(self.detail))
                lineup = d['lineups']['home']
                if variant == 'incomplete': lineup['players'].pop()
                if variant == 'duplicate': lineup['players'][0]['espnId'] = '1'
                if variant == 'unconfirmed': lineup['confirmed'] = False
                if variant == 'wrong-team': lineup['name'] = 'Other'
                if variant == 'wrong-league': d['league'] = 'ucl'
                self.write('match-details/a.json', d)
                coaches._cache.clear()
                self.assertEqual(coaches.coach_lineups('epl', 1)['matches'], [])

    def test_cache_refreshes_changed_local_snapshot(self):
        self.write('match-details/a.json', self.detail)
        self.assertEqual(coaches.coach_lineups('epl', 1)['matches'][0]['formation'], '4-3-3')
        self.detail['lineups']['home']['formation'] = '4-4-2'
        self.write('match-details/a.json', self.detail)
        with patch.object(coaches.time, 'monotonic', return_value=1e15):
            self.assertEqual(coaches.coach_lineups('epl', 1)['matches'][0]['formation'], '4-4-2')
