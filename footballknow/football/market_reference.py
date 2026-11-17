"""Dated policy rates and HK stock breadth, refreshed at modest intervals."""
import csv
import io
import json
import re
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

from .files import fetch_text, publish
from .finance import FOLDER, HK, load, now, number
from .racing import age

RATE_NAMES = {
    'US': ('USD', '联邦基金目标区间中点'), 'XM': ('EUR', '存款便利利率'),
    'GB': ('GBP', '银行利率'), 'AU': ('AUD', '现金利率目标'),
    'NZ': ('NZD', '官方现金利率'), 'JP': ('JPY', '无担保隔夜拆借利率目标'),
    'CN': ('CNY', '1 年期贷款市场报价利率 LPR'), 'HK': ('HKD', '基本利率'),
    'CA': ('CAD', '隔夜利率目标'), 'CH': ('CHF', '瑞士央行政策利率'),
    'KR': ('KRW', '韩国银行基准利率'), 'IN': ('INR', '政策回购利率'),
}
BIS_SOURCE = 'https://data.bis.org/topics/CBPOL'
TW_SOURCE = 'https://www.cbc.gov.tw/tw/lp-640-1.html'
SG_SOURCE = 'https://www.mas.gov.sg/monetary-policy/Singapores-Monetary-Policy-Framework/faqs/section-2'
RANK_COLUMNS = ['name', 'close', 'change', 'high', 'low', 'price_52_week_high', 'price_52_week_low', 'volume', 'currency', 'type', 'time']


def rate_changes(points):
    points = sorted(dict(points).items())
    if not points:
        return None
    date, rate = points[-1]
    changes = [(points[i][0], points[i][1], points[i - 1][1]) for i in range(1, len(points))
               if abs(points[i][1] - points[i - 1][1]) > 0.000001]
    changed = changes[-1] if changes else None
    return {'rate': rate, 'asOf': date, 'changedAt': changed[0] if changed else None,
            'previousRate': changed[2] if changed else None,
            'changeBp': round((changed[1] - changed[2]) * 100, 4) if changed else None}


def parse_bis(raw, fetched_at):
    series, metadata = defaultdict(list), {}
    for row in csv.DictReader(io.StringIO(raw.lstrip('\ufeff'))):
        area = row.get('REF_AREA')
        value = number(row.get('OBS_VALUE'))
        date = row.get('TIME_PERIOD', '')
        if area not in RATE_NAMES or row.get('FREQ') != 'D' or row.get('UNIT_MEASURE') != '368' or row.get('UNIT_MULT') != '0':
            continue
        if value is None or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date) or date > fetched_at[:10]:
            continue
        series[area].append((date, value))
        metadata[area] = row
    result = {}
    for area, points in series.items():
        currency, label = RATE_NAMES[area]
        result[currency] = {**rate_changes(points), 'name': label, 'currency': currency,
                            'authority': metadata[area]['SOURCE_REF'], 'definition': metadata[area]['COMPILATION'],
                            'provider': 'BIS / 各地央行', 'source': BIS_SOURCE, 'fetchedAt': fetched_at}
    if 'CNY' in result:
        result['CNH'] = {**result['CNY'], 'currency': 'CNH', 'name': '人民币政策参考：1 年期 LPR',
                         'note': '与在岸人民币共用政策参考，不是离岸存款利率。'}
    return result


def parse_taiwan(raw, fetched_at):
    points = []
    for row in BeautifulSoup(raw, 'html.parser').select('table tr'):
        cells = [c.get_text(' ', strip=True) for c in row.find_all(['td', 'th'], recursive=False)]
        if len(cells) < 4 or not re.fullmatch(r'\d{4}/\d{1,2}/\d{1,2}', cells[0]):
            continue
        date = datetime.strptime(cells[0], '%Y/%m/%d').date().isoformat()
        value = number(cells[1])
        if value is not None and date <= fetched_at[:10]:
            points.append((date, value))
    result = rate_changes(points)
    if not result:
        raise ValueError('重贴现率表格不可用')
    return {**result, 'asOf': fetched_at[:10], 'currency': 'TWD', 'name': '重贴现率',
            'authority': '中央银行', 'provider': '中央银行', 'source': TW_SOURCE, 'fetchedAt': fetched_at}


def refresh_policy_rates():
    path = FOLDER / 'policy-rates.json'
    previous = load(path)
    if age(previous.get('checkedAt')) < (3600 if previous.get('failed') else 86400):
        return previous
    stamp = now()
    rates, failed = dict(previous.get('rates', {})), []
    start = (datetime.now(timezone.utc) - timedelta(days=1461)).date().isoformat()
    url = 'https://stats.bis.org/api/v1/data/WS_CBPOL/D.' + '+'.join(RATE_NAMES) + '?startPeriod=' + start + '&format=csvfile'
    try:
        fresh = parse_bis(fetch_text(url), stamp)
        if len(fresh) < 10:
            raise ValueError('政策利率来源不完整')
        rates.update(fresh)
        failed.extend(c for c, _ in RATE_NAMES.values() if c not in fresh)
    except (OSError, ValueError):
        failed.append('BIS')
    try:
        rates['TWD'] = parse_taiwan(fetch_text(TW_SOURCE), stamp)
    except (OSError, ValueError):
        failed.append('TWD')
    rates['SGD'] = {'currency': 'SGD', 'rate': None, 'name': '汇率政策框架', 'changeBp': None,
                    'note': '新加坡以贸易加权汇率为政策工具，没有可直接对应的单一政策利率。',
                    'authority': '新加坡金融管理局', 'provider': 'MAS', 'source': SG_SOURCE}
    result = {'checkedAt': stamp, 'rates': rates, 'failed': failed,
              'method': '利率为年率；最近变动从同一官方日度序列计算，100 个基点=1个百分点。BIS 数据通常每周发布，并非实时央行公告。'}
    publish(path, result)
    return result


def normalize_rankings(payload, catalogue, fetched_at):
    allowed = {'HKEX:' + str(int(r['code'])): r for r in catalogue if re.fullmatch(r'\d{5}', r.get('code', ''))}
    rows = []
    for item in payload.get('data', []):
        stock = allowed.get(item.get('s'))
        values = item.get('d', [])
        if stock is None or len(values) != len(RANK_COLUMNS):
            continue
        q = dict(zip(RANK_COLUMNS, values))
        if str(q['name']) != str(int(stock['code'])) or q['currency'] != stock['currency'] or q['type'] not in {'stock', 'dr', 'fund'}:
            continue
        price, change, epoch = number(q['close'], True), number(q['change']), number(q['time'], True)
        if price is None or epoch is None:
            continue
        quoted = datetime.fromtimestamp(epoch, timezone.utc)
        if quoted > datetime.fromisoformat(fetched_at) + timedelta(minutes=5):
            continue
        hi, lo = number(q['price_52_week_high'], True), number(q['price_52_week_low'], True)
        if hi is not None and lo is not None and hi < lo:
            hi = lo = None
        rows.append({'code': stock['code'], 'name': stock['name'], 'currency': q['currency'],
                     'price': price, 'changePercent': change, 'high': number(q['high'], True), 'low': number(q['low'], True),
                     'high52': hi, 'low52': lo, 'volume': number(q['volume']),
                     'quotedAt': quoted.isoformat(), 'tradeDate': quoted.astimezone(HK).date().isoformat(),
                     'fetchedAt': fetched_at, 'source': 'https://www.tradingview.com/symbols/HKEX-' + str(int(stock['code'])) + '/',
                     'provider': 'TradingView'})
    return rows


def refresh_stock_rankings():
    path = FOLDER / 'stock-rankings.json'
    previous = load(path)
    if age(previous.get('fetchedAt')) < 600:
        return previous
    catalogue = load(FOLDER / 'stocks.json').get('stocks', [])
    tickers = ['HKEX:' + str(int(r['code'])) for r in catalogue if re.fullmatch(r'\d{5}', r.get('code', ''))]
    if not tickers:
        raise ValueError('港股名单尚未提供')
    payload = {'symbols': {'tickers': tickers}, 'columns': RANK_COLUMNS}
    req = urllib.request.Request('https://scanner.tradingview.com/hongkong/scan',
            data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json', 'User-Agent': 'FootballKnow/3.0'})
    with urllib.request.urlopen(req, timeout=25) as response:
        raw = response.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError('排行来源超过大小限制')
    stamp = now()
    rows = normalize_rankings(json.loads(raw), catalogue, stamp)
    if len(rows) < min(100, len(catalogue) // 2):
        raise ValueError('排行行情覆盖不足，保留原资料')
    result = {'fetchedAt': stamp, 'rows': rows, 'requested': len(catalogue),
              'tradeDate': max(r['tradeDate'] for r in rows), 'provider': 'TradingView',
              'method': '按同一交易日涨跌幅排列；排除无成交和报价日期不一致的记录。52周区间采用同一行情源的高低位。'}
    publish(path, result)
    return result
