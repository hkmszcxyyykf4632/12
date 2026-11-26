import csv
import io
import unittest
from unittest.mock import patch
from tools.handicap_study import LEAGUES, handicap, parse, profit, settlement, summary


class HandicapStudyTests(unittest.TestCase):
    def parse_rows(self, records, expected=None):
        columns = ['Div', 'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR', 'AHCh', 'AHh', 'B365CAHH', 'B365CAHA']
        buffer = io.StringIO()
        w = csv.DictWriter(buffer, fieldnames=columns)
        w.writeheader()
        for n, record in enumerate(records):
            w.writerow({'Div': 'E0', 'Date': f'{n+1:02}/08/2025', 'HomeTeam': 'Home', 'AwayTeam': 'Away',
                        'FTHG': '1', 'FTAG': '1', 'FTR': 'D', 'AHCh': '-0.5', 'AHh': '-0.25',
                        'B365CAHH': '1.9', 'B365CAHA': '2.0', **record})
        with patch.dict(LEAGUES, {'epl': ('英超', 'E0', len(records) if expected is None else expected)}):
            return parse(buffer.getvalue().encode(), '2025-26', 'epl', 'https://example.test/E0.csv')

    def test_closing_only_no_early_fallback_and_both_home_away(self):
        rows, audit, _ = self.parse_rows([{'AHCh': x} for x in ['-.5', '-.25', '0', '.25', '.5', '.75', '']])
        self.assertEqual([r['line'] for r in rows], [-.5, -.25, 0, .25, .5])
        self.assertEqual(audit['selected'], 5)
        self.assertEqual(audit['missingClosingLine'], 1)
        self.assertEqual(audit['outsideScope'], 1)

    def test_reject_corrupt_result_and_incomplete_season(self):
        with self.assertRaises(ValueError):
            self.parse_rows([{'FTR': 'H'}])
        with self.assertRaises(ValueError):
            self.parse_rows([{}], expected=380)

    def test_duplicate_not_double_counted(self):
        rows, audit, _ = self.parse_rows([{'Date': '01/08/2025'}, {'Date': '01/08/2025'}], expected=1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(audit['duplicate'], 1)

    def test_quarter_line_settlement_and_price_dependent_returns(self):
        self.assertEqual(settlement(0, -.25), -.5)
        self.assertEqual(settlement(0, .25), .5)
        self.assertEqual(settlement(0, 0), 0)
        self.assertEqual(settlement(1, -.5), 1)
        self.assertAlmostEqual(profit(0, .25, 1.9), .45)
        self.assertEqual(profit(0, -.25, 1.9), -.5)
        self.assertAlmostEqual(profit(0, .25, 1.9) + profit(0, -.25, 1.9), -.05)

    def test_invalid_line_and_price_are_not_zeros(self):
        for x in ['NaN', 'inf', '', None, '.3']:
            self.assertIsNone(handicap(x))
        rows, _, _ = self.parse_rows([{'B365CAHH': '', 'B365CAHA': '2'}])
        s = summary(rows)
        self.assertEqual(s['sides']['lower']['n'], 1)
        self.assertEqual(s['sides']['lower']['pricedN'], 0)
        self.assertIsNone(s['sides']['lower']['roiPct'])

    def test_distance_sign_inclusive_boundary_and_conditional_denominators(self):
        rows, _, _ = self.parse_rows([
            {'FTHG': '1', 'FTAG': '0', 'FTR': 'H'},
            {'FTHG': '0', 'FTAG': '1', 'FTR': 'A'},
            {'FTHG': '0', 'FTAG': '0', 'FTR': 'D'},
            {'FTHG': '2', 'FTAG': '2', 'FTR': 'D'},
        ])
        self.assertEqual([r['distance'] for r in rows], [.5, 1.5, .5, .5])
        s = summary(rows)
        self.assertEqual(s['bands']['0.5']['count'], 3)
        self.assertEqual(s['halfBall']['lowerWin']['count'], 3)
        self.assertEqual(s['halfBall']['fixed00or11']['pct'], 25)
        self.assertEqual(s['halfBall']['draw00or11GivenLowerWin']['n'], 3)
        self.assertEqual(s['halfBall']['draw00or11GivenLowerWin']['pct'], 33.33)
        self.assertEqual(s['halfBall']['underdogOutrightWins'], 1)
        self.assertEqual(s['halfBall']['otherDraws'], 1)

    def test_away_favorite_orientation_and_pickem_has_no_upper_lower(self):
        rows, _, _ = self.parse_rows([{'AHCh': '.5', 'AHh': '.25', 'FTHG': '0', 'FTAG': '2', 'FTR': 'A'},
                                    {'AHCh': '0', 'AHh': '-.25'}])
        self.assertEqual(rows[0]['movement'], '让球加深')
        s = summary(rows)
        self.assertEqual(s['favoriteScores'][0]['score'], '2:0')
        self.assertEqual(s['sides']['upper']['n'], 1)
        self.assertEqual(s['sides']['upper']['outcomes']['全赢'], 1)
        self.assertEqual(s['sides']['home']['n'], 2)


if __name__ == '__main__':
    unittest.main()
