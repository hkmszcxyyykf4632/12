import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from unittest.mock import patch
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor

from football import videos, visits


class SiteContentTests(unittest.TestCase):
    def test_visit_counter_is_persistent_and_retry_safe(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'counter.db'
            self.assertEqual(visits.counter(path=path)['total'], visits.BASE)
            event = str(uuid4())
            self.assertEqual(visits.counter(event, path)['total'], visits.BASE + 1)
            self.assertEqual(visits.counter(event, path)['total'], visits.BASE + 1)
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(lambda _: visits.counter(str(uuid4()), path), range(20)))
            self.assertEqual(visits.counter(path=path), {'total': visits.BASE + 21, 'base': visits.BASE, 'added': 21})

    def test_visit_base_migration_preserves_added_and_retry_history(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'counter.db'
            event = str(uuid4())
            visits.counter(event, path)
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('UPDATE totals SET base=100000,added=123 WHERE id=1')
            self.assertEqual(visits.BASE, 35_627_892)
            self.assertEqual(visits.counter(event, path), {'total': 35_628_015, 'base': 35_627_892, 'added': 123})
            self.assertEqual(visits.counter(str(uuid4()), path)['added'], 124)

    def test_drafts_and_unpublishing(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(videos, 'PATH', Path(folder) / 'videos.json'):
            value = videos.VideoInput(title='赛后分析', url='https://example.com/video.mp4')
            saved = videos.save(value)
            self.assertEqual(videos.catalogue()['videos'], [])
            self.assertEqual(saved['playback']['kind'], 'file')
            value.published = True
            videos.save(value, saved['id'])
            self.assertEqual(len(videos.catalogue()['videos']), 1)
            value.published = False
            videos.save(value, saved['id'])
            self.assertEqual(videos.catalogue()['videos'], [])
            self.assertEqual(len(videos.catalogue(True)['videos']), 1)

    def test_embed_hosts_and_invalid_links(self):
        self.assertEqual(videos.playback('https://youtube.com.evil.test/watch?v=abcdef12345')['kind'], 'link')
        self.assertEqual(videos.playback('https://youtu.be/abcdef12345')['url'], 'https://www.youtube-nocookie.com/embed/abcdef12345')
        for url in ['javascript:alert(1)', 'http://example.com/test.mp4', 'https://user:pass@example.com/a.mp4']:
            with self.assertRaises(ValueError):
                videos.VideoInput(title='test', url=url)


if __name__ == '__main__':
    unittest.main()
