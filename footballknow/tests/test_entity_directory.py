import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from football import entity_directory as entities


class EntityDirectoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patcher = patch.object(entities, 'PUBLIC', self.root)
        self.patcher.start()
        entities._cache.clear()
        self.write('data.json', {'teams': [{'id': 1, 'name': 'Arsenal', 'cn': '阿森纳'}, {'id': 15, 'name': 'Man City', 'cn': '曼城'}]})
        self.write('ucl/data.json', {'teams': [{'id': 359, 'espnId': 359, 'name': 'Arsenal', 'cn': '阿森纳'}, {'id': 382, 'espnId': 382, 'name': 'Manchester City', 'cn': '曼城'}]})
        self.write('laliga/data.json', {'teams': [{'id': 1, 'name': 'Other', 'cn': '另一队'}]})
        self.write('racing/directory.json', {'horses': [{'id': 'HK_A', 'name': '甲马', 'owner': '甲/乙 團體', 'trainer': {'id': 'T1', 'name': '甲师'}}]})
        self.write('racing/people.json', {'season': '2026', 'jockeys': [{'id': 'J1', 'name': '甲骑', 'numStarts': 99, 'numFirst': 12}], 'trainers': [{'id': 'T1', 'name': '甲师'}]})
        self.write('racing/races/r1.json', {'id': 'r1', 'date': '2026-11-20', 'raceNo': 1, 'resultOfficial': True, 'entries': [
            {'id': 'HK_A', 'name': '甲马', 'owner': '旧马主', 'jockey': {'id': 'J1', 'name': '甲骑'}, 'trainer': {'id': 'T1', 'name': '甲师'}, 'place': 1}]})

    def tearDown(self):
        self.patcher.stop()
        entities._cache.clear()
        self.temp.cleanup()

    def write(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value), encoding='utf-8')

    def test_clubs_are_shared_across_competitions_without_numeric_id_collision(self):
        teams = [e for e in entities.entity_index()['entities'] if e['kind'] == 'team']
        self.assertEqual(len(teams), 3)
        arsenal = next(t for t in teams if t['name'] == '阿森纳')
        self.assertEqual([t['id'] for t in arsenal['targets']], ['1', '359'])
        city = next(t for t in teams if t['name'] == '曼城')
        self.assertEqual(set(city['aliases']), {'曼城', 'Man City', 'Manchester City'})

    def test_owner_current_horses_are_not_retroactively_attributed_old_results(self):
        current = entities.racing_person('owner', '甲/乙 團體')
        self.assertEqual(len(current['horses']), 1)
        self.assertEqual(current['entries'], [])
        old = entities.racing_person('owner', '旧马主')
        self.assertEqual(old['horses'], [])
        self.assertEqual(len(old['entries']), 1)
        names = [e['name'] for e in entities.entity_index()['entities'] if e['kind'] == 'owner']
        self.assertIn('旧马主', names)

    def test_jockey_profile_uses_official_season_totals_and_saved_race_links(self):
        person = entities.racing_person('jockey', 'J1')
        self.assertEqual(person['person']['numStarts'], 99)
        self.assertEqual(len(person['entries']), 1)
        self.assertEqual(person['horses'][0]['id'], 'HK_A')
        with self.assertRaises(LookupError):
            entities.racing_person('jockey', '../secret')
        self.assertEqual(entities.person_id({'source': 'https://racing.hkjc.com/jockeyprofile?jockeyid=J1'}, 'jockey'), 'J1')

    def test_new_saved_data_is_visible_after_cache_refresh(self):
        self.assertEqual(len(entities.racing_person('trainer', 'T1')['horses']), 1)
        self.write('racing/directory.json', {'horses': []})
        with patch.object(entities.time, 'monotonic', return_value=1e15):
            self.assertEqual(len(entities.racing_person('trainer', 'T1')['horses']), 0)
