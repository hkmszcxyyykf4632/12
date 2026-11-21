"""Publish one watched-stock forecast per run after observing today's trading data."""
import math
from datetime import datetime, time, timedelta, timezone

from . import ai
from .files import STATE, publish
from .finance import FOLDER, HK, load, stock
from .reviews import watched_codes, require_watched
from .stock_service import viewed_quotes
from .sync_control import read_control


def timestamp(value):
    try:
        result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return result if result.tzinfo else None
    except (ValueError, TypeError):
        return None


def session_window(code, at):
    local = at.astimezone(HK)
    close = time(15) if len(code) == 6 else time(16)
    return local.weekday() < 5 and time(9, 35) <= local.time() < close


def cached_quote(code):
    base = load(FOLDER / ('cn-quotes.json' if len(code) == 6 else 'quotes.json')).get('quotes', {}).get(code, {})
    cached = load(FOLDER / 'quote-cache' / (code + '.json'))
    return max([base, cached], key=lambda q: timestamp(q.get('fetchedAt')) or datetime.min.replace(tzinfo=timezone.utc))


def automatic_snapshot(code, at, quote=None):
    if not read_control()['enabled']:
        raise ValueError('同步已暂停。')
    require_watched(code)
    item = stock(code)
    if not item or not session_window(code, at):
        raise ValueError('等待本市场交易日的日间发布时段。')
    quote = cached_quote(code) if quote is None else quote
    fetched = timestamp(quote.get('fetchedAt'))
    traded = timestamp(quote.get('quotedAt') or (quote.get('barAt') if len(code) == 6 else None))
    price = quote.get('price')
    if (quote.get('code') != code or not isinstance(price, (int, float)) or isinstance(price, bool)
            or not math.isfinite(price) or price <= 0 or not fetched or not traded
            or not timedelta(0) <= at - fetched <= timedelta(minutes=15)
            or traded > at or traded.astimezone(HK).date() != at.astimezone(HK).date()
            or quote.get('currency') != item.get('currency', 'CNY' if len(code) == 6 else 'HKD')):
        raise ValueError('尚未取得本交易日可核对的有效报价，不使用假日或停牌前旧行情。')
    if len(code) != 6 and (traded.astimezone(HK).time() < time(9, 30) or at - traded > timedelta(minutes=30)):
        raise ValueError('本股行情尚未确认当日交易，等待下一轮。')
    return quote


def refresh(at=None):
    from .stock_analysis import connect, generate, VERSION
    fixed_at = at
    at = at or datetime.now(timezone.utc)
    if not read_control()['enabled']:
        return {'generated': 0, 'paused': True}
    codes = [code for code in dict.fromkeys(watched_codes()) if stock(code) and session_window(code, at)]
    if not codes:
        return {'generated': 0, 'message': '等待已关注股票的交易时段。'}
    if not ai.settings().apiKey.get_secret_value():
        return {'generated': 0, 'message': '分析服务尚未配置。'}
    day = at.astimezone(HK).date().isoformat()
    with connect() as db:
        published = {row['code'] for row in db.execute('SELECT code FROM forecasts WHERE day=? AND version=?', (day, VERSION))}
    attempts_path = STATE / 'stock-forecast-attempts.json'
    attempts = load(attempts_path)
    for code in sorted(codes, key=lambda c: attempts.get(c, '')):
        previous = timestamp(attempts.get(code))
        if code in published or previous and at - previous < timedelta(minutes=10):
            continue
        attempts[code] = at.isoformat()
        publish(attempts_path, {c: stamp for c, stamp in attempts.items() if c in codes})
        try:
            quote = viewed_quotes([code]).get('quotes', {}).get(code, {})
            automatic_snapshot(code, fixed_at or datetime.now(timezone.utc), quote)
            result = generate(code, automatic=True)
        except (OSError, ValueError, LookupError):
            return {'generated': 0, 'checked': 1, 'code': code, 'message': '本股资料或分析暂不可用，稍后自动重试。'}
        latest = result.get('latest') or {}
        issued = timestamp(latest.get('issuedAt'))
        generated = bool(issued and issued.astimezone(HK).date().isoformat() == day and latest.get('version') == VERSION)
        return {'generated': int(generated), 'code': code}
    return {'generated': 0}
