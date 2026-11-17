"""Serve the full catalogue with bounded, cached requests for a viewed stock."""
import threading
import time
from datetime import datetime, timezone

from .finance import FOLDER, load, now, stock, parse_tencent, request, refresh_company, refresh_history
from .files import publish
from .sync_control import read_control

DETAIL_LOCK = threading.Lock()
QUOTE_LOCK = threading.Lock()
ATTEMPTS = {}


def age(value):
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(value)).total_seconds()
    except (TypeError, ValueError):
        return float('inf')


def viewed_quotes(codes):
    codes = list(dict.fromkeys(codes))
    if not codes or len(codes) > 50 or any(code != 'HSI' and not stock(code) for code in codes):
        raise ValueError('报价请求仅限名单内的 1 至 50 只股票。')
    base = load(FOLDER / 'quotes.json').get('quotes', {})
    rows = {code: base[code] for code in codes if code in base}
    for code in codes:
        cached = load(FOLDER / 'quote-cache' / (code + '.json'))
        if cached.get('code') == code and age(cached.get('fetchedAt')) < age(rows.get(code, {}).get('fetchedAt')):
            rows[code] = cached
    stale = [code for code in codes if age(rows.get(code, {}).get('fetchedAt')) > 55]
    if stale and read_control()['enabled'] and QUOTE_LOCK.acquire(blocking=False):
        try:
            stamp = now()
            parsed = parse_tencent(request('https://qt.gtimg.cn/q=' + ','.join('hk' + c for c in stale), 'gb18030'), set(stale), stamp)
            for code, quote in parsed.items():
                item = stock(code)
                if item:
                    quote['currency'] = item.get('currency', 'HKD')
                    quote['unit'] = {'HKD': '港元', 'CNY': '人民币', 'RMB': '人民币', 'USD': '美元'}.get(quote['currency'], quote['currency'])
                publish(FOLDER / 'quote-cache' / (code + '.json'), quote)
            rows.update(parsed)
        except (OSError, ValueError, UnicodeError):
            pass
        finally:
            QUOTE_LOCK.release()
    return {'version': 1, 'updatedAt': now(), 'quotes': rows,
            'failedCodes': [code for code in codes if age(rows.get(code, {}).get('fetchedAt')) > 180],
            'paused': not read_control()['enabled']}


def detail(code, kind):
    item = stock(code)
    if not item:
        raise LookupError('Unknown stock')
    if kind not in {'companies', 'history'}:
        raise ValueError('Unknown stock detail')
    path = FOLDER / kind / (code + '.json')
    cached = load(path)
    ttl = 86400 if kind == 'companies' else 3600
    if age(cached.get('checkedAt') or cached.get('updatedAt')) <= ttl and (kind != 'companies' or cached.get('leadership') or 'leadership' in cached.get('failedSections', [])):
        return cached
    if not read_control()['enabled']:
        return {**item, **cached, 'paused': True, 'message': '同步已暂停，正在显示已保存的资料。'}
    key = (code, kind)
    if time.monotonic() - ATTEMPTS.get(key, -float('inf')) < 300:
        return {**item, **cached, 'message': '来源暂未更新，保留最近资料。'}
    if not DETAIL_LOCK.acquire(blocking=False):
        return {**item, **cached, 'pending': True, 'message': '资料读取排队中。'}
    try:
        ATTEMPTS[key] = time.monotonic()
        return (refresh_company if kind == 'companies' else refresh_history)(code)
    except (OSError, ValueError, KeyError, TypeError):
        return {**item, **cached, 'message': '来源暂未提供本项资料，稍后自动重试。'}
    finally:
        DETAIL_LOCK.release()
