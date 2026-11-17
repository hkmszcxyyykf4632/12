"""Anonymous read-only queries published by HKJC's public information pages."""
import json
import gzip
import urllib.request
from pathlib import Path

from .files import LIMIT, USER_AGENT

ENDPOINT = 'https://info.cld.hkjc.com/graphql/base/'


def query(name, variables):
    path = Path(__file__).with_name('hkjc_queries') / (name + '.graphql')
    body = json.dumps({'query': path.read_text(encoding='utf-8'), 'variables': variables}).encode()
    request = urllib.request.Request(ENDPOINT, data=body, headers={
        'Content-Type': 'application/json', 'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=25) as response:
        raw = response.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('马会数据超过读取上限。')
    if raw.startswith(b'\x1f\x8b'):
        raw = gzip.decompress(raw)
        if len(raw) > LIMIT:
            raise ValueError('马会数据超过读取上限。')
    result = json.loads(raw)
    if result.get('errors') or not isinstance(result.get('data'), dict):
        raise ValueError('马会公开数据暂时不可用。')
    return result['data']
