"""Bounded public-source requests and atomic JSON publication."""
import hashlib
import json
import os
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Final

from pydantic import JsonValue

ROOT: Final = Path(__file__).resolve().parent.parent
PUBLIC: Final = ROOT / 'public'
STATE: Final = Path(os.environ.get('FOOTBALL_STATE_DIR', str(ROOT / 'state')))
USER_AGENT: Final = 'FootballKnow/2.0 (+https://footballknow.art)'


LIMIT: Final = 16 * 1024 * 1024


def _cache_paths(url: str) -> tuple[Path, Path]:
    folder = STATE / 'http-cache'
    key = hashlib.sha256(url.encode('utf-8')).hexdigest()
    return folder / f'{key}.json', folder / f'{key}.body'


def _validators(meta_path: Path, body_path: Path) -> dict[str, str]:
    """Conditional headers for a body already held; none if the pair is incomplete."""
    try:
        if not body_path.is_file():
            return {}
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    headers = {}
    if isinstance(meta.get('etag'), str):
        headers['If-None-Match'] = meta['etag']
    if isinstance(meta.get('lastModified'), str):
        headers['If-Modified-Since'] = meta['lastModified']
    return headers


def _remember(meta_path: Path, body_path: Path, raw: bytes, etag: str | None, modified: str | None) -> None:
    if not etag and not modified:
        return
    try:
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        for path, content in [(body_path, raw), (meta_path, json.dumps({'etag': etag, 'lastModified': modified}).encode())]:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
                output.write(content)
            os.chmod(output.name, 0o600)
            os.replace(output.name, path)
    except OSError:
        pass  # The cache only saves bandwidth; a read-only state directory must not fail a refresh.


def fetch_text(url: str) -> str:
    """Read a public source every time it is asked for, revalidating instead of re-downloading.

    Jobs run once a minute. Sources that publish an ETag or Last-Modified answer an
    unchanged page with 304, so the minute cadence costs them a header exchange.
    """
    meta_path, body_path = _cache_paths(url)
    conditional = _validators(meta_path, body_path)
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': '*/*', **conditional})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read(LIMIT + 1)
            etag, modified = response.headers.get('ETag'), response.headers.get('Last-Modified')
    except urllib.error.HTTPError as error:
        if error.code != 304 or not conditional:
            raise
        raw = body_path.read_bytes()
        etag = modified = None
    if len(raw) > LIMIT:
        raise OSError('Public source response exceeds the size limit')
    _remember(meta_path, body_path, raw, etag, modified)
    return raw.decode('utf-8-sig')


def publish(path: Path, value: JsonValue) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        json.dump(value, output, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    try:
        temporary.chmod(0o644 if path.resolve().is_relative_to(PUBLIC.resolve()) else 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path: Path) -> JsonValue:
    return json.loads(path.read_text(encoding='utf-8'))
