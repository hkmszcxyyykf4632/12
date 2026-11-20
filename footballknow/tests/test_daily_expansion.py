import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from football.equity_markets import quote_from_scan, checked_rows
from football.stock_volume import volume_row


class DailyExpansionTests(unittest.TestCase):
    def test_culture_counter_http_contract(self):
        spec = importlib.util.spec_from_file_location('culture_counter', Path(__file__).parents[1] / 'deploy/culture_counter_service.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            module.CounterHandler.db_path = Path(folder) / 'visits.db'
            server = ThreadingHTTPServer(('127.0.0.1', 0), module.CounterHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f'http://127.0.0.1:{server.server_port}/api/visits'
            def post(event, origin='https://tripitaka.shop'):
                request = Request(url, data=json.dumps({'event': event}).encode(), headers={'Content-Type': 'application/json', 'Origin': origin})
                with urlopen(request) as response:
                    return json.load(response)
            try:
                with urlopen(url) as response:
                    self.assertEqual(json.load(response), {'total': 100000})
                event = str(uuid4())
                self.assertEqual(post(event), {'total': 100001})
                self.assertEqual(post(event), {'total': 100001})
                self.assertEqual(post(str(uuid4())), {'total': 100002})
                for value, origin, status in [('bad', 'https://tripitaka.shop', 400), (str(uuid4()), 'https://example.com', 403)]:
                    with self.assertRaises(HTTPError) as caught:
                        post(value, origin)
                    self.assertEqual(caught.exception.code, status)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_volume_units_thresholds_and_source_day(self):
        stamp = '2026-11-20T05:00:00+00:00'
        raw = {'time': datetime(2026, 11, 20, 1, 30, tzinfo=timezone.utc).timestamp(),
               'volume': 300000, 'average_volume_60d_calc': 90000, 'average_volume_90d_calc': 95000}
        item = {'code': '00001', 'name': 'test', 'market': 'hk', 'symbol': 'HKEX:1'}
        row = volume_row(item, raw, stamp)
        self.assertTrue(row['low'] and row['spike'] and row['currentDay'])
        self.assertFalse(row['closed'])
        self.assertEqual(row['volume'], 300000)
        self.assertFalse(volume_row(item, {**raw, 'average_volume_90d_calc': 100001}, stamp)['low'])
        self.assertIsNone(volume_row(item, {**raw, 'average_volume_60d_calc': 0}, stamp))
        self.assertFalse(volume_row(item, raw, '2026-11-21T05:00:00+00:00')['currentDay'])

    def test_quote_identity_and_bar_time_not_trade_timestamp(self):
        raw = {'close': 12.3, 'currency': 'CNY', 'time': 1795138200, 'update_mode': 'delayed_streaming_900'}
        result = quote_from_scan('600000', 'SSE:600000', raw, '2026-11-20T05:00:00+00:00', 'CNY')
        self.assertIsNone(result['quotedAt'])
        self.assertEqual(result['delaySeconds'], 900)
        self.assertIsNone(quote_from_scan('600000', 'SSE:600000', raw, '2026-11-20T05:00:00+00:00', 'USD'))
        with self.assertRaises(ValueError):
            checked_rows([{'SECUCODE': '000001.SZ'}], '600000.SH')
