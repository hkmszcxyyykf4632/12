"""Independent quote feeds with explicit timing and instrument identity."""
import json
import re
import urllib.request
from datetime import datetime, timedelta

from .finance import number, request

FUTURES = {'COMEX:GC1!': 'gold', 'NYMEX:CL1!': 'wti', 'ICEEUR:BRN1!': 'brent'}


def parse_futures(payload, stamp):
    rows = {}
    for row in payload.get('data', []):
        symbol, values = row.get('s'), row.get('d', [])
        if symbol not in FUTURES or len(values) != 7 or values[4] != 'USD' or values[6] != 'futures':
            continue
        price = number(values[2], True)
        if price is None or values[0] != symbol.split(':')[1]:
            continue
        delay_match = re.fullmatch(r'delayed_streaming_(\d+)', values[5] or '')
        delay = int(delay_match[1]) if delay_match else None
        rows[FUTURES[symbol]] = {'symbol': symbol, 'price': price, 'changePercent': number(values[3]),
            'change': None, 'changeBasis': '较上一交易日', 'quotedAt': None, 'fetchedAt': stamp,
            'currency': 'USD', 'instrumentType': 'FUTURE', 'contract': symbol + ' 连续期货',
            'provider': 'TradingView', 'source': 'https://www.tradingview.com/symbols/' + symbol.replace(':', '-') + '/',
            'delaySeconds': delay, 'timeliness': ('延迟约 ' + str(delay // 60) + ' 分钟') if delay else '来源未注明固定延时'}
    return rows


def parse_bitcoin(ticker, stats, stamp):
    price = number(ticker.get('price'), True)
    quoted = datetime.fromisoformat(ticker['time'].replace('Z', '+00:00'))
    if price is None or quoted.tzinfo is None or quoted > datetime.fromisoformat(stamp) + timedelta(minutes=5):
        raise ValueError('Invalid Coinbase quote')
    opening = number(stats.get('open'), True)
    return {'symbol': 'BTC-USD', 'price': price, 'currency': 'USD', 'instrumentType': 'CRYPTOCURRENCY',
            'contract': 'Coinbase BTC-USD', 'provider': 'Coinbase Exchange',
            'source': 'https://exchange.coinbase.com/trade/BTC-USD', 'quotedAt': quoted.isoformat(),
            'fetchedAt': stamp, 'change': price - opening if opening else None,
            'changePercent': (price / opening - 1) * 100 if opening else None,
            'changeBasis': '24 小时', 'timeliness': '交易所最近成交快照'}


def alternative_assets(stamp):
    rows = {}
    try:
        body = {'symbols': {'tickers': list(FUTURES), 'query': {'types': []}},
                'columns': ['name', 'description', 'close', 'change', 'currency', 'update_mode', 'type']}
        req = urllib.request.Request('https://scanner.tradingview.com/futures/scan', data=json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read(100001)
        if len(raw) > 100000:
            raise ValueError('Oversized futures response')
        rows.update(parse_futures(json.loads(raw), stamp))
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        ticker = json.loads(request('https://api.exchange.coinbase.com/products/BTC-USD/ticker'))
        try:
            stats = json.loads(request('https://api.exchange.coinbase.com/products/BTC-USD/stats'))
        except (OSError, ValueError):
            stats = {}
        rows['bitcoin'] = parse_bitcoin(ticker, stats, stamp)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return rows
