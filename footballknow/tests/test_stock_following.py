import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from football import stock_following as store


def change(code, following=True, ident=None):
    return {'id': ident or str(uuid4()), 'code': code, 'following': following}


class FollowingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patcher = patch.object(store, 'PATH', Path(self.temp.name)/'following.sqlite3')
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp.cleanup()

    def test_pair_two_devices_merges_existing_lists_then_syncs_deletions(self):
        _, phone = store.connect()
        _, desktop = store.connect()
        _, stranger = store.connect()
        store.apply(phone, [change('00700'), change('00005')])
        store.apply(desktop, [change('00001')])
        code = store.make_pair(phone)['code']
        joined = store.join_pair(desktop, code)
        self.assertEqual(joined['codes'], ['00001', '00005', '00700'])
        self.assertEqual(joined['devices'], 2)
        self.assertEqual(store.connect(phone)[0]['codes'], store.connect(desktop)[0]['codes'])
        self.assertEqual(store.connect(stranger)[0]['codes'], [])
        store.apply(desktop, [change('00700', False), change('600000')])
        self.assertEqual(store.connect(phone)[0]['codes'], ['00001', '00005', '600000'])
        with self.assertRaises(ValueError): store.join_pair(stranger, code)
        self.assertEqual(store.connect(stranger)[0]['codes'], [])

    def test_offline_retry_does_not_resurrect_later_deletion(self):
        _, token = store.connect()
        original = change('00700')
        store.apply(token, [original])
        store.apply(token, [change('00700', False)])
        self.assertEqual(store.apply(token, [original])['codes'], [])
        _, other = store.connect()
        pair = store.make_pair(token)['code']
        store.join_pair(other, pair)
        self.assertEqual(store.apply(other, [original])['codes'], [])

    def test_bad_expired_codes_and_unauthenticated_mutations_fail_closed(self):
        _, phone = store.connect()
        _, desktop = store.connect()
        code = store.make_pair(phone)['code']
        with patch.object(store.time, 'time', return_value=1e15):
            with self.assertRaises(ValueError): store.join_pair(desktop, code)
        for action in [lambda: store.apply('bad', [change('00001')]), lambda: store.make_pair('bad'), lambda: store.join_pair('bad', code)]:
            with self.assertRaises(PermissionError): action()
        for _ in range(10):
            with self.assertRaises(ValueError): store.join_pair(desktop, 'NOT-A-VALID-CODE')
        with self.assertRaisesRegex(ValueError, '十分钟'):
            store.join_pair(desktop, code)

    def test_concurrent_independent_changes_are_preserved(self):
        _, token = store.connect()
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda i: store.apply(token, [change(f'{i:05}')]), range(20)))
        self.assertEqual(len(store.connect(token)[0]['codes']), 20)

    def test_http_device_pairing_cookie_security_and_origin_boundary(self):
        from fastapi.testclient import TestClient
        from server import app
        from football.stock_following_api import COOKIE
        headers = {'Origin': 'http://testserver'}
        with patch.dict('os.environ', {'FOOTBALL_PRODUCTION': '0'}):
            a, b, visitor = [TestClient(app, headers=headers) for _ in range(3)]
            first = a.get('/api/stocks/following')
            self.assertEqual(first.status_code, 200)
            self.assertIn('httponly', first.headers['set-cookie'].lower())
            self.assertEqual(first.headers['cache-control'], 'no-store')
            self.assertTrue(a.cookies.get(COOKIE))
            b.get('/api/stocks/following')
            self.assertEqual(visitor.post('/api/stocks/following', json={'changes': [change('00001')]}).status_code, 401)
            a.post('/api/stocks/following', json={'changes': [change('00700')]})
            b.post('/api/stocks/following', json={'changes': [change('00005')]})
            code = a.post('/api/stocks/following/pair').json()['code']
            joined = b.post('/api/stocks/following/join', json={'code': code})
            self.assertEqual(joined.status_code, 200)
            self.assertEqual(joined.json()['codes'], ['00005', '00700'])
            self.assertEqual(a.get('/api/stocks/following').json()['codes'], joined.json()['codes'])
            self.assertEqual(a.post('/api/stocks/following/pair', headers={'Origin': 'https://bad.example'}).status_code, 403)
            self.assertEqual(visitor.get('/api/stocks/following').json()['codes'], [])
            self.assertEqual(a.post('/api/stocks/following', json={'changes': [change('../state')]}).status_code, 422)
            for client in (a, b, visitor): client.close()
