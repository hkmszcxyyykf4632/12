"""Kickoff forecasts, cached by venue city and never reconstructed after kickoff."""
import gzip
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache
from pathlib import Path
import unicodedata
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .files import STATE, publish
from .motivation import dt

BASE = 'https://api.met.no/weatherapi/locationforecast/2.0/compact'
ALIASES = {'wien': 'vienna', 'roma': 'rome', 'munchen': 'munich', 'milano': 'milan', 'koln': 'cologne',
           'napoli': 'naples', 'firenze': 'florence', 'lisboa': 'lisbon', 'sevilla': 'seville'}


def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value)).lower() if c.isalnum() and not unicodedata.combining(c))


@lru_cache(maxsize=1)
def geography():
    data = json.loads(Path(__file__).with_name('cities.json').read_text('utf-8'))
    countries = {norm(k): v for k, v in data['countries'].items()}
    countries.update({norm(k): 'GB' for k in ['England', 'Scotland', 'Wales', 'Northern Ireland', 'UK']})
    countries.update({'usa': 'US', 'unitedstatesofamerica': 'US', 'southkorea': 'KR'})
    index = {}
    for city in data['cities']:
        for name in {norm(city['name']), norm(city['ascii'])}:
            index.setdefault((city['country'], name), []).append(city)
    return countries, index


def locate(venue):
    address = venue.get('address') or {}
    countries, cities = geography()
    country = countries.get(norm(address.get('country')))
    name = norm(address.get('city'))
    matches = cities.get((country, ALIASES.get(name, name)), [])
    if len(matches) != 1:
        return None
    return {**matches[0], 'basis': '球场所在城市参考点，非球场实测'}


def load(path):
    try:
        return json.loads(path.read_text('utf-8'))
    except (OSError, ValueError):
        return {}


def parse_forecast(raw, kickoff, location, fetched_at):
    items = [(dt(r.get('time')), r) for r in raw.get('properties', {}).get('timeseries', [])]
    items = [(stamp, row) for stamp, row in items if stamp]
    if not items:
        return {'status': '预报资料不足'}
    stamp, row = min(items, key=lambda pair: abs((pair[0] - kickoff).total_seconds()))
    if abs((stamp - kickoff).total_seconds()) > 3 * 3600:
        return {'status': '尚未进入预报覆盖时间'}
    details = row.get('data', {}).get('instant', {}).get('details', {})
    period = next((p for p in ['next_1_hours', 'next_6_hours'] if p in row.get('data', {})), None)
    rain = row['data'][period].get('details', {}).get('precipitation_amount') if period else None
    t, wind, humidity = (details.get(k) for k in ['air_temperature', 'wind_speed', 'relative_humidity'])
    notes = []
    if isinstance(t, (int, float)) and t >= 28:
        notes.append('气温偏高，持续逼抢和后半程体能需要关注；具体影响还取决于湿度与球员适应。')
    if isinstance(t, (int, float)) and t <= 2:
        notes.append('气温较低，留意场地结冰、热身和临场场地报告。')
    if isinstance(wind, (int, float)) and wind >= 8:
        notes.append('风力偏大，长传、传中和门将处理高球可能受到影响。')
    if isinstance(rain, (int, float)) and rain >= 1:
        notes.append('预报有降水，关注草皮排水、球速和失误；降水量不能直接证明场地积水。')
    if not notes:
        notes.append('已取得的温度、风速与降水未触发本站的关注阈值；仍需结合临场场地情况。')
    return {'status': 'available', 'location': location, 'forecastFor': stamp.isoformat(), 'fetchedAt': fetched_at,
            'modelUpdatedAt': raw.get('properties', {}).get('meta', {}).get('updated_at'),
            'temperature': t, 'windSpeed': wind, 'humidity': humidity, 'precipitation': rain,
            'precipitationHours': 1 if period == 'next_1_hours' else 6 if period else None,
            'notes': notes, 'source': 'https://www.met.no/', 'sourceLabel': 'MET Norway Locationforecast',
            'license': 'https://creativecommons.org/licenses/by/4.0/', 'geoSource': 'https://www.geonames.org/',
            'method': '整理预报数值并按本站关注阈值解读；不是胜率增减模型。'}


def forecast(venue, kickoff, at):
    if at >= kickoff:
        return {'status': '比赛已开始，仅展示留存的赛前预报'}
    if os.environ.get('FOOTBALL_MET_TERMS_ACCEPTED') != '1':
        return {'status': '天气接口待启用'}
    location = locate(venue)
    if not location:
        return {'status': '球场城市位置尚未唯一核实'}
    url = f'{BASE}?lat={location["latitude"]:.4f}&lon={location["longitude"]:.4f}'
    path = STATE / 'weather' / (hashlib.sha256(url.encode()).hexdigest() + '.json')
    saved = load(path)
    if not dt(saved.get('nextCheck')) or at >= dt(saved['nextCheck']):
        next_check = at + timedelta(hours=3, seconds=int(location['id']) % 600)
        headers = {'User-Agent': 'FootballKnow/3.0 https://inwesting.shop', 'Accept-Encoding': 'gzip'}
        if saved.get('modified') and saved.get('raw'):
            headers['If-Modified-Since'] = saved['modified']
        try:
            with urlopen(Request(url, headers=headers), timeout=20) as response:
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise ValueError('Weather response too large')
                if response.headers.get('Content-Encoding') == 'gzip':
                    raw = gzip.decompress(raw)
                if len(raw) > 8_000_000:
                    raise ValueError('Weather response too large')
                expires = response.headers.get('Expires')
                if expires:
                    next_check = max(next_check, parsedate_to_datetime(expires))
                saved = {'raw': json.loads(raw), 'fetchedAt': at.isoformat(), 'modified': response.headers.get('Last-Modified')}
        except HTTPError as error:
            if error.code == 304:
                saved['fetchedAt'] = at.isoformat()
            else:
                saved['error'] = '天气来源暂时不可用'
                if error.code in {403, 429}:
                    next_check = at + timedelta(days=1)
        except (OSError, ValueError):
            saved['error'] = '天气来源暂时不可用'
        saved['nextCheck'] = next_check.isoformat()
        publish(path, saved)
    result = parse_forecast(saved.get('raw', {}), kickoff, location, saved.get('fetchedAt'))
    if saved.get('error'):
        result['refreshMessage'] = saved['error']
    return result
