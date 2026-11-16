"""Bounded public-source requests and atomic JSON publication."""
import json
import os
import tempfile
import urllib.request
from pathlib import Path
from typing import Final

from pydantic import JsonValue

ROOT: Final = Path(__file__).resolve().parent.parent
PUBLIC: Final = ROOT / 'public'
STATE: Final = Path(os.environ.get('FOOTBALL_STATE_DIR', str(ROOT / 'state')))
USER_AGENT: Final = 'FootballKnow/2.0 (+https://footballknow.art)'


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': '*/*'})
    with urllib.request.urlopen(request, timeout=25) as response:
        raw = response.read(16 * 1024 * 1024 + 1)
    if len(raw) > 16 * 1024 * 1024:
        raise OSError('Public source response exceeds the size limit')
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
