"""One bounded quote request for indices, continuous futures and USD crosses."""
import json
import math
import re
import urllib.request
from datetime import datetime, timezone
from .files import PUBLIC, publish, read_json

PATH = PUBLIC / 'finance' / 'global-markets.json'
ENDPOINT = 'https://scanner.tradingview.com/global/scan'
COLUMNS = ['name', 'description', 'close', 'change', 'change_abs', 'open', 'high', 'low', 'update_mode', 'type', 'currency']
INDEX_ROWS = [
    ('SP:SPX', '标普500', '美洲', '美国'), ('DJ:DJI', '道琼斯工业平均', '美洲', '美国'),
    ('TVC:IXIC', '纳斯达克综合', '美洲', '美国'), ('TSX:TSX', '加拿大S&P/TSX综合', '美洲', '加拿大'),
    ('TVC:UKX', '英国富时100', '欧洲', '英国'), ('XETR:DAX', '德国DAX', '欧洲', '德国'),
    ('EURONEXT:PX1', '法国CAC40', '欧洲', '法国'), ('STOXX:SX5E', '欧洲斯托克50', '欧洲', '欧元区'),
    ('TVC:NI225', '日经225', '亚洲', '日本'), ('TVC:KOSPI', '韩国综合KOSPI', '亚洲', '韩国'),
    ('SSE:000001', '上证综合指数', '亚洲', '中国内地'), ('SZSE:399001', '深证成份指数', '亚洲', '中国内地'),
    ('HSI:HSI', '恒生指数', '亚洲', '中国香港'), ('SP:XJO', '澳大利亚S&P/ASX200', '大洋洲', '澳大利亚'),
    ('NSE:NIFTY', '印度Nifty50', '亚洲', '印度'), ('BMFBOVESPA:IBOV', '巴西IBOVESPA', '美洲', '巴西'),
    ('TVC:FTMIB', '意大利FTSE MIB', '欧洲', '意大利'), ('IDX:COMPOSITE', '印尼雅加达综合', '亚洲', '印度尼西亚'),
    ('TVC:SA40', '南非Top40', '非洲', '南非'), ('TADAWUL:TASI', '沙特TASI', '中东', '沙特阿拉伯'),
]
COMMODITY_ROWS = [
    ('COMEX:GC1!', '黄金', '贵金属', '金衡盎司'), ('COMEX:SI1!', '白银', '贵金属', '金衡盎司'),
    ('NYMEX:PL1!', '铂金', '贵金属', '金衡盎司'), ('NYMEX:PA1!', '钯金', '贵金属', '金衡盎司'),
    ('NYMEX:CL1!', 'WTI原油', '原油', '桶'), ('ICEEUR:BRN1!', '布伦特原油', '原油', '桶'),
]
FX_ROWS = [
    ('EUR', '欧元', '欧元区', True), ('GBP', '英镑', '英国', True), ('AUD', '澳元', '澳大利亚', True),
    ('NZD', '新西兰元', '新西兰', True), ('JPY', '日元', '日本', False),
    ('CNY', '人民币（在岸）', '中国内地', False), ('CNH', '人民币（离岸）', '离岸市场', False),
    ('HKD', '港元', '中国香港', False), ('CAD', '加元', '加拿大', False), ('CHF', '瑞士法郎', '瑞士', False),
    ('SGD', '新加坡元', '新加坡', False), ('KRW', '韩元', '韩国', False),
    ('TWD', '新台币', '中国台湾', False), ('INR', '印度卢比', '印度', False),
]
INSTRUMENTS = [dict(symbol=s, name=n, category='indices', group=g, country=c, unit='点', expectedType='index') for s,n,g,c in INDEX_ROWS]
INSTRUMENTS += [dict(symbol=s, name=n, category='commodities', group=g, unit='美元/'+u, expectedType='futures', expectedCurrency='USD') for s,n,g,u in COMMODITY_ROWS]
INSTRUMENTS += [dict(symbol='FX_IDC:'+(c+'USD' if direct else 'USD'+c), name=n, category='forex', group='主要货币', country=country, currencyCode=c, direct=direct, expectedType='forex', expectedCurrency='USD' if direct else c) for c,n,country,direct in FX_ROWS]
INSTRUMENTS.append(dict(symbol='TVC:DXY', name='美元指数', category='dollarIndex', group='美元', country='美国', unit='点', expectedType='index'))
DEFINITIONS = {row['symbol']: row for row in INSTRUMENTS}


def number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def normalize(payload, fetched_at):
    result = {}
    for row in payload.get('data', []):
        definition = DEFINITIONS.get(row.get('s'))
        values = row.get('d', [])
        if not definition or len(values) != len(COLUMNS):
            continue
        raw = dict(zip(COLUMNS, values))
        if raw['name'] != definition['symbol'].split(':', 1)[1] or raw['type'] != definition['expectedType']:
            continue
        if definition.get('expectedCurrency') and raw['currency'] != definition['expectedCurrency']:
            continue
        price, percent = number(raw['close']), number(raw['change'])
        if price is None or price <= 0:
            continue
        delay = re.fullmatch(r'delayed_streaming_(\d+)', str(raw['update_mode']))
        quote = {k:v for k,v in definition.items() if not k.startswith('expected')}
        quote.update(price=price, changePercent=percent, change=number(raw['change_abs']),
                     open=number(raw['open']), high=number(raw['high']), low=number(raw['low']),
                     fetchedAt=fetched_at, quotedAt=None, delaySeconds=int(delay[1]) if delay else None,
                     updateMode=raw['update_mode'], source='TradingView',
                     sourceUrl='https://www.tradingview.com/symbols/'+definition['symbol'].replace(':','-')+'/',
                     description=raw['description'])
        if definition['category'] == 'forex':
            direct = definition['direct']
            quote.update(usdPerUnit=price if direct else 1/price, unitsPerUsd=1/price if direct else price,
                         rawChangePercent=percent,
                         changePercent=percent if direct else ((1/(1+percent/100)-1)*100 if percent is not None and percent > -100 else None))
        result[definition['symbol']] = quote
    return result


def merge_quotes(previous, fresh, checked_at):
    old = {q['symbol']:q for q in previous.get('quotes', []) if q.get('symbol') in DEFINITIONS}
    quotes = []
    for definition in INSTRUMENTS:
        symbol = definition['symbol']
        quote = fresh.get(symbol) or old.get(symbol) or {k:v for k,v in definition.items() if not k.startswith('expected')}
        quotes.append({**quote, 'lastCheckOk': symbol in fresh})
    return {'version': 1, 'checkedAt': checked_at, 'updatedAt': checked_at if fresh else previous.get('updatedAt'),
            'quotes': quotes, 'failedSymbols': [q['symbol'] for q in quotes if not q['lastCheckOk']]}


def refresh_global_markets():
    stamp = datetime.now(timezone.utc).isoformat()
    try:
        previous = read_json(PATH)
    except (OSError, ValueError):
        previous = {}
    body = json.dumps({'symbols': {'tickers': list(DEFINITIONS), 'query': {'types': []}}, 'columns': COLUMNS}).encode()
    request = urllib.request.Request(ENDPOINT, data=body, headers={'Content-Type':'application/json', 'User-Agent':'FootballKnow/2.0 (+https://footballknow.art)'})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(100_001)
        if len(raw) > 100_000:
            raise ValueError('Quote response exceeds limit')
        fresh = normalize(json.loads(raw), stamp)
    except (OSError, ValueError, TypeError, AttributeError):
        fresh = {}
    result = merge_quotes(previous, fresh, stamp)
    publish(PATH, result)
    return result
