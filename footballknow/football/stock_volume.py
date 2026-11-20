"""Source-day volume against source 60/90-session averages, without annualization."""
from datetime import datetime, timedelta, timezone
from .equity_markets import scan, scan_rows
from .finance import FOLDER, HK, load, now, number
from .files import publish

THRESHOLDS = {'hk': 100000, 'cn': 1000000}
METHOD = '长期低成交候选：来源 60 日和 90 日日均成交股数均低于阈值（港股 10 万股、沪深 100 万股）。突然放量：来源当日累计成交量达到 60 日均量的 3 倍。盘中累计量不年化，不把半日量当成全天量；来源均量可能随当日日线变化。'


def volume_row(item, raw, stamp):
    current, avg60, avg90 = (number(raw.get(k)) for k in ('volume', 'average_volume_60d_calc', 'average_volume_90d_calc'))
    epoch = number(raw.get('time'), True)
    if epoch is None or current is None or current < 0 or avg60 is None or avg90 is None or avg60 <= 0 or avg90 <= 0:
        return None
    day_at = datetime.fromtimestamp(epoch, timezone.utc).astimezone(HK)
    checked = datetime.fromisoformat(stamp).astimezone(HK)
    if day_at > checked + timedelta(minutes=5):
        return None
    threshold = THRESHOLDS[item['market']]
    low = avg60 < threshold and avg90 < threshold
    ratio = current / avg60
    trade_day = day_at.date().isoformat()
    current_day = day_at.date() == checked.date()
    close_hour = 16 if item['market'] == 'hk' else 15
    closed = day_at.date() < checked.date() or (checked.hour, checked.minute) >= (close_hour, 20)
    return {'code': item['code'], 'name': item['name'], 'market': item['market'], 'volume': current,
        'average10': number(raw.get('average_volume_10d_calc')), 'average30': number(raw.get('average_volume_30d_calc')),
        'average60': avg60, 'average90': avg90, 'threshold': threshold, 'low': low, 'ratio': ratio,
        'spike': low and ratio >= 3, 'currentDay': current_day, 'closed': closed,
        'tradeDate': trade_day, 'fetchedAt': stamp, 'unit': '股', 'provider': 'TradingView',
        'updateMode': raw.get('update_mode'),
        'source': 'https://www.tradingview.com/symbols/' + item['symbol'].replace(':', '-') + '/'}


def refresh_volume():
    stamp = now()
    old = load(FOLDER / 'stock-volume.json')
    rows = dict(old.get('rows', {}))
    failures, updated = [], []
    cn = load(FOLDER / 'cn-volume-source.json')
    cn_items = {r['code']: r for r in load(FOLDER / 'cn-stocks.json').get('stocks', [])}
    try:
        age = (datetime.fromisoformat(stamp) - datetime.fromisoformat(cn.get('updatedAt', ''))).total_seconds()
        if age > 900 or age < 0:
            raise ValueError('CN volume snapshot stale')
        for entry in cn.get('rows', []):
            item = cn_items.get(entry.get('code'))
            if item and (row := volume_row(item, entry.get('raw', {}), cn['updatedAt'])):
                rows[item['code']] = row
        updated.append('cn')
    except (ValueError, TypeError):
        failures.append('cn')
    try:
        items = {str(int(r['code'])): {**r, 'market': 'hk', 'symbol': 'HKEX:' + str(int(r['code']))}
                 for r in load(FOLDER / 'stocks.json').get('stocks', []) if r.get('currency') == 'HKD' and str(r.get('code', '')).isdigit()}
        payload = scan('hongkong', {'filter': [{'left': 'type', 'operation': 'equal', 'right': 'stock'}],
                                   'range': [0, 10000], 'sort': {'sortBy': 'name', 'sortOrder': 'asc'}})
        parsed = scan_rows(payload)
        if len(parsed) != payload.get('totalCount') or len(parsed) < 1000:
            raise ValueError('Incomplete Hong Kong volume scan')
        for symbol, raw in parsed:
            item = items.get(str(raw.get('name')))
            if item and item['symbol'] == symbol and raw.get('currency') == 'HKD' and (row := volume_row(item, raw, stamp)):
                rows[item['code']] = row
        updated.append('hk')
    except (OSError, ValueError, TypeError, KeyError):
        failures.append('hk')
    if not updated:
        raise OSError('No volume source updated')
    allowed = set(cn_items) | {r['code'] for r in load(FOLDER / 'stocks.json').get('stocks', [])}
    rows = {k: v for k, v in rows.items() if k in allowed}
    publish(FOLDER / 'stock-volume.json', {'version': 1, 'updatedAt': stamp, 'rows': rows,
        'failedMarkets': failures, 'method': METHOD, 'covered': len(rows), 'catalogueTotal': len(allowed)})
    return {'covered': len(rows), 'low': sum(r['low'] for r in rows.values()), 'failedMarkets': failures}
