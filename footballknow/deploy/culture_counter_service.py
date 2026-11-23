"""Small loopback-only service for the separate culture homepage counter."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

try:
    from football.visits import counter
except ImportError:
    from visits import counter


class CounterHandler(BaseHTTPRequestHandler):
    db_path = Path(os.environ.get('CULTURE_STATE_DIR', '/var/lib/jingzang-counter')) / 'visits.sqlite3'
    allowed_origins = {'https://tripitaka.shop', 'https://www.tripitaka.shop'}

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def reply(self, status, data):
        raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if urlsplit(self.path).path != '/api/visits':
            return self.reply(404, {'error': 'Not found'})
        self.reply(200, {'total': counter(path=self.db_path, initial_base=100000)['total']})

    def do_POST(self):
        if urlsplit(self.path).path != '/api/visits':
            return self.reply(404, {'error': 'Not found'})
        if self.headers.get('Origin') not in self.allowed_origins:
            return self.reply(403, {'error': 'Origin not allowed'})
        if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
            return self.reply(415, {'error': 'JSON required'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 1024 or self.headers.get('Transfer-Encoding'):
                return self.reply(413, {'error': 'Invalid request size'})
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict) or set(data) != {'event'} or not isinstance(data['event'], str):
                raise ValueError('Invalid event')
            result = counter(data['event'], self.db_path, initial_base=100000)
        except (ValueError, TypeError, UnicodeError):
            return self.reply(400, {'error': 'Invalid event'})
        self.reply(200, {'total': result['total']})

    def log_message(self, *_):
        pass


if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', 8766), CounterHandler).serve_forever()
