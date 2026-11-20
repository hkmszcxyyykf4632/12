import unittest
from football.horse_going import going_group, going_performance


class GoingTests(unittest.TestCase):
    def test_turf_and_all_weather_are_separate(self):
        self.assertEqual(going_group({'surface': '草地', 'going': '好/黏'}), 'yielding')
        self.assertEqual(going_group({'surface': '草地', 'going': '黏/軟'}), 'soft')
        self.assertEqual(going_group({'surface': '全天候跑道', 'going': '濕慢'}), 'wet')
        self.assertIsNone(going_group({'surface': '首爾/沙地跑道', 'going': '受天雨影響'}))
        self.assertIsNone(going_group({'surface': '草地', 'going': '未知'}))

    def test_small_sample_duplicate_and_withdrawal(self):
        base = {'surface': '草地', 'going': '軟', 'place': 1, 'date': '2026-11-01'}
        rows = [{**base, 'raceId': str(i)} for i in range(4)]
        rows += [rows[0], {**base, 'raceId': 'withdrawn', 'withdrawn': True}]
        sample = next(r for r in going_performance(rows) if r['group'] == 'soft')
        self.assertEqual(sample['starts'], 4)
        self.assertFalse(sample['strong'])
        rows.append({**base, 'raceId': 'fifth', 'place': None})
        sample = next(r for r in going_performance(rows) if r['group'] == 'soft')
        self.assertEqual(sample['starts'], 5)
        self.assertEqual(sample['wins'], 4)
        self.assertTrue(sample['strong'])


if __name__ == '__main__':
    unittest.main()
