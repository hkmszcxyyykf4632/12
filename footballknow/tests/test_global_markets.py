import unittest
from football.global_markets import normalize, merge_quotes


class GlobalMarketsTest(unittest.TestCase):
    def row(self, symbol, price=150, percent=10, kind='forex', currency='JPY'):
        return {'s':symbol, 'd':[symbol.split(':')[1], 'label', price, percent, 1, price, price, price, 'delayed_streaming_600', kind, currency]}

    def test_inverse_direction_and_percentage(self):
        q = normalize({'data':[self.row('FX_IDC:USDJPY')]}, 'now')['FX_IDC:USDJPY']
        self.assertAlmostEqual(q['usdPerUnit'], 1/150)
        self.assertEqual(q['unitsPerUsd'], 150)
        self.assertAlmostEqual(q['changePercent'], -9.09090909)
        self.assertEqual(q['delaySeconds'], 600)
        self.assertIsNone(q['quotedAt'])

    def test_direct_and_null_change(self):
        q = normalize({'data':[self.row('FX_IDC:EURUSD',1.1,None,currency='USD')]}, 'now')['FX_IDC:EURUSD']
        self.assertEqual(q['usdPerUnit'],1.1)
        self.assertIsNone(q['changePercent'])

    def test_wrong_identity_type_currency_rejected(self):
        wrong = self.row('FX_IDC:USDJPY'); wrong['d'][0]='EURUSD'
        rows = [wrong, self.row('FX_IDC:USDJPY',kind='stock'),self.row('FX_IDC:USDJPY',currency='USD'),self.row('UNKNOWN:XYZ')]
        self.assertEqual(normalize({'data':rows},'now'),{})

    def test_failure_preserves_quote_and_original_timestamp(self):
        quote=normalize({'data':[self.row('FX_IDC:USDJPY')]},'old')
        old=merge_quotes({},quote,'old')
        result=merge_quotes(old,{},'new')
        q=next(q for q in result['quotes'] if q['symbol']=='FX_IDC:USDJPY')
        self.assertEqual(q['fetchedAt'],'old')
        self.assertEqual(result['updatedAt'],'old')
        self.assertFalse(q['lastCheckOk'])
        self.assertEqual(result['checkedAt'],'new')

    def test_null_nan_and_zero_quotes_not_fabricated(self):
        self.assertEqual(normalize({'data':[self.row('FX_IDC:USDJPY',value) for value in [None,0,float('nan')]]},'now'),{})
