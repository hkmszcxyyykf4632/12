"""Administrator-authored video catalogue. Drafts remain private."""
import re
import threading
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from .files import STATE, publish, read_json

LOCK = threading.Lock()
PATH = STATE / 'videos.json'


def public_url(value):
    if not value:
        return ''
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise ValueError('请使用完整的 HTTPS 链接。')
    if parsed.hostname in {'localhost', '127.0.0.1', '::1'}:
        raise ValueError('请使用访客可以访问的视频地址。')
    return value


def playback(value):
    parsed = urlsplit(public_url(value))
    host = parsed.hostname
    if re.search(r'\.(mp4|webm)$', parsed.path, re.I):
        return {'kind': 'file', 'url': value}
    ident = None
    if host == 'youtu.be':
        ident = parsed.path.strip('/')
    elif host in {'youtube.com', 'www.youtube.com', 'm.youtube.com'}:
        ident = parse_qs(parsed.query).get('v', [None])[0] if parsed.path == '/watch' else parsed.path.split('/')[-1] if parsed.path.startswith(('/shorts/', '/embed/')) else None
    if ident and re.fullmatch(r'[A-Za-z0-9_-]{11}', ident):
        return {'kind': 'youtube', 'url': 'https://www.youtube-nocookie.com/embed/' + ident}
    return {'kind': 'link', 'url': value}


class VideoInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=3000)
    category: Literal['football', 'racing', 'stocks', 'markets', 'other'] = 'other'
    url: str = Field(min_length=8, max_length=2000)
    poster: str = Field(default='', max_length=2000)
    published: bool = False

    @field_validator('title')
    @classmethod
    def title_not_blank(cls, value):
        if not value.strip():
            raise ValueError('标题不能为空')
        return value.strip()

    @field_validator('url', 'poster')
    @classmethod
    def check_url(cls, value, info):
        value = value.strip()
        if info.field_name == 'url' and not value:
            raise ValueError('视频链接不能为空')
        return public_url(value)


def catalogue(admin=False):
    try:
        data = read_json(PATH)
    except FileNotFoundError:
        data = {'version': 1, 'videos': []}
    rows = data.get('videos', [])
    return {'version': 1, 'updatedAt': data.get('updatedAt'),
            'videos': sorted([r for r in rows if admin or r.get('published')], key=lambda r: r.get('publishedAt') or r['createdAt'], reverse=True)}


def save(value, ident=None):
    with LOCK:
        data = catalogue(True)
        rows = data['videos']
        old = next((r for r in rows if r['id'] == ident), None) if ident else None
        if ident and not old:
            raise LookupError('视频不存在')
        if not ident and len(rows) >= 1000:
            raise ValueError('视频目录已达到 1000 条')
        stamp = datetime.now(timezone.utc).isoformat()
        row = {**value.model_dump(), 'id': ident or uuid4().hex, 'createdAt': old['createdAt'] if old else stamp,
               'updatedAt': stamp, 'publishedAt': (old or {}).get('publishedAt') or (stamp if value.published else None),
               'playback': playback(value.url)}
        rows = [r for r in rows if r['id'] != row['id']] + [row]
        publish(PATH, {'version': 1, 'updatedAt': stamp, 'videos': rows})
        return row
