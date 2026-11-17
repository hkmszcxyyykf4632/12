"""Dated public market snapshots. Prices and financial statements keep separate units."""
import json
import math
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

from .files import PUBLIC, publish, read_json

FOLDER = PUBLIC / 'finance'
HK = timezone(timedelta(hours=8))
_STOCK_VERSION = None
_STOCK_INDEX = {}
EASTMONEY = 'https://datacenter.eastmoney.com/securities/api/data/v1/get'
ASSETS = {
    'gold': ('GC=F', 'COMEX 黄金期货', '美元/金衡盎司'),
    'brent': ('BZ=F', '布伦特原油期货', '美元/桶'),
    'wti': ('CL=F', 'WTI 原油期货', '美元/桶'),
    'bitcoin': ('BTC-USD', '比特币', '美元/枚'),
}


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path, default=None):
    try:
        value = read_json(path)
        finance = value.get('financials') if isinstance(value, dict) else None
        if isinstance(finance, dict) and finance.get('statements') and not finance.get('amountCurrency'):
            # Eastmoney HK PC statement amounts are converted to CNY, unlike report-header currency.
            for rows in finance['statements'].values():
                for row in rows:
                    row['reportCurrency'] = row.get('currency')
                    row['currency'] = '人民币'
            finance['amountCurrency'] = 'CNY'
            finance['currencyBasis'] = '东方财富统一折算人民币；报告原币种另存。'
        return value
    except (OSError, ValueError):
        return {} if default is None else default


def number(value, positive=False):
    if isinstance(value, bool) or value is None or value == '':
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) and (not positive or result > 0) else None
    except (ValueError, TypeError):
        return None


def request(url, encoding='utf-8'):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 FootballKnow/3.0', 'Accept': 'application/json,text/plain,*/*'})
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024:
        raise ValueError('Market response too large')
    return raw.decode(encoding)


def constituents():
    rows = read_json(FOLDER / 'constituents.json')['constituents']
    if len(rows) < 50 or len({r['code'] for r in rows}) != len(rows):
        raise ValueError('Invalid constituent catalogue')
    return rows


def stock(code):
    global _STOCK_VERSION, _STOCK_INDEX
    path = FOLDER / 'stocks.json'
    version = (str(path), path.stat().st_mtime_ns if path.exists() else None)
    if version != _STOCK_VERSION:
        rows = load(path).get('stocks') or constituents()
        _STOCK_INDEX = {row['code']: row for row in rows}
        _STOCK_VERSION = version
    return _STOCK_INDEX.get(code)


def parse_tencent(raw, expected, fetched_at):
    rows = {}
    for code, body in re.findall(r'v_hk([A-Za-z0-9]+)="([^"\n]+)"', raw):
        parts = body.split('~')
        if code not in expected or len(parts) < 35 or parts[2] != code:
            continue
        try:
            timestamp = datetime.strptime(parts[30], '%Y/%m/%d %H:%M:%S').replace(tzinfo=HK)
            if timestamp > datetime.fromisoformat(fetched_at) + timedelta(minutes=5):
                continue
        except ValueError:
            continue
        price = number(parts[3], True)
        if price is None:
            continue
        rows[code] = {'code': code, 'name': parts[1], 'price': price,
                      'previousClose': number(parts[4], True), 'open': number(parts[5], True),
                      'change': number(parts[31]), 'changePercent': number(parts[32]),
                      'high': number(parts[33], True), 'low': number(parts[34], True),
                      'quotedAt': timestamp.isoformat(), 'fetchedAt': fetched_at,
                      'currency': 'HKD' if code != 'HSI' else None,
                      'unit': '港元' if code != 'HSI' else '点', 'provider': '腾讯行情',
                      'source': 'https://gu.qq.com/hk' + code,
                      'timeliness': '参考行情；来源未注明固定延时'}
    return rows


def refresh_quotes():
    codes = ['HSI'] + [r['code'] for r in constituents()]
    stamp = now()
    previous = load(FOLDER / 'quotes.json').get('quotes', {})
    quotes, updated = dict(previous), set()
    for offset in range(0, len(codes), 40):
        batch = codes[offset:offset + 40]
        try:
            parsed = parse_tencent(request('https://qt.gtimg.cn/q=' + ','.join('hk' + c for c in batch), 'gb18030'), set(batch), stamp)
            quotes.update(parsed)
            updated.update(parsed)
        except (OSError, ValueError, UnicodeError):
            pass
    if not updated:
        raise OSError('Market quotes unavailable; previous snapshot retained')
    result = {'version': 1, 'updatedAt': stamp, 'quotes': quotes, 'failedCodes': [c for c in codes if c not in updated]}
    publish(FOLDER / 'quotes.json', result)
    return result


def chart(symbol, span='1y'):
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/' + urllib.parse.quote(symbol, safe='')
    payload = json.loads(request(url + '?interval=1d&range=' + span + '&events=div%2Csplits'))
    result = payload.get('chart', {}).get('result')
    if not result or result[0].get('meta', {}).get('symbol') != symbol:
        raise ValueError('Price history identity mismatch')
    return result[0]


def normalize_chart(raw, fetched_at):
    meta = raw['meta']
    times = raw.get('timestamp') or []
    values = (raw.get('indicators', {}).get('quote') or [{}])[0]
    adjusted = (raw.get('indicators', {}).get('adjclose') or [{}])[0].get('adjclose') or []
    bars = []
    for i, epoch in enumerate(times):
        if not isinstance(epoch, (int, float)):
            continue
        def at(key):
            array = values.get(key) or []
            return number(array[i]) if i < len(array) else None
        close = at('close')
        if close is None or close <= 0:
            continue
        stamp = datetime.fromtimestamp(epoch, timezone.utc)
        if stamp > datetime.fromisoformat(fetched_at):
            continue
        bars.append({'timestamp': stamp.isoformat(), 'date': stamp.astimezone(HK).date().isoformat(),
                     'close': close, 'adjustedClose': number(adjusted[i], True) if i < len(adjusted) else None,
                     'open': at('open'), 'high': at('high'), 'low': at('low'), 'volume': at('volume')})
    return {'version': 1, 'symbol': meta['symbol'], 'currency': meta.get('currency'), 'updatedAt': fetched_at,
            'provider': 'Yahoo Finance', 'source': 'https://finance.yahoo.com/quote/' + urllib.parse.quote(meta['symbol'], safe=''),
            'bars': sorted({b['date']: b for b in bars}.values(), key=lambda b: b['date'])}


def refresh_assets():
    from .market_sources import alternative_assets
    path = FOLDER / 'assets.json'
    rows = dict(load(path).get('assets', {}))
    failed = []
    stamp = now()
    alternatives = alternative_assets(stamp)
    for key, (symbol, label, unit) in ASSETS.items():
        if key in alternatives:
            old = rows.get(key, {})
            history = old.get('history') or ({k: old.get(k) for k in ['bars', 'provider', 'source', 'updatedAt', 'symbol']} if old.get('bars') else None)
            rows[key] = {**alternatives[key], 'id': key, 'name': label, 'unit': unit, 'updatedAt': stamp,
                         'history': history}
            continue
        try:
            raw = chart(symbol, '3mo')
            meta = raw['meta']
            price = number(meta.get('regularMarketPrice'), True)
            quoted = datetime.fromtimestamp(meta['regularMarketTime'], timezone.utc)
            if price is None or meta.get('currency') != 'USD' or quoted > datetime.fromisoformat(stamp) + timedelta(minutes=5):
                raise ValueError('Invalid asset quote')
            rows[key] = {**normalize_chart(raw, stamp), 'id': key, 'name': label, 'unit': unit,
                         'contract': meta.get('shortName'), 'instrumentType': meta.get('instrumentType'),
                         'price': price, 'quotedAt': quoted.isoformat(),
                         'change': number(meta.get('fulldayChange')), 'changePercent': number(meta.get('regularMarketChangePercent')),
                         'timeliness': '参考行情；来源报价时间随数据展示'}
        except (OSError, ValueError, KeyError, TypeError):
            failed.append(key)
    if len(failed) == len(ASSETS):
        raise OSError('Asset quotes unavailable')
    result = {'version': 1, 'updatedAt': stamp, 'assets': rows, 'failedAssets': failed}
    publish(path, result)
    return result


def normalize_em_history(payload, code, currency, fetched_at):
    data = payload.get('data') or {}
    if data.get('code') != code:
        raise ValueError('History identity mismatch')
    bars = []
    for raw in data.get('klines', []):
        parts = raw.split(',')
        if len(parts) < 6:
            continue
        day = datetime.strptime(parts[0], '%Y-%m-%d').replace(tzinfo=HK)
        close = number(parts[2], True)
        if day > datetime.fromisoformat(fetched_at) or close is None:
            continue
        bars.append({'date': parts[0], 'timestamp': day.isoformat(), 'open': number(parts[1]),
                     'close': close, 'adjustedClose': close, 'high': number(parts[3]),
                     'low': number(parts[4]), 'volume': number(parts[5])})
    if not bars:
        raise ValueError('Empty adjusted price history')
    return {'version': 1, 'code': code, 'symbol': code + '.HK', 'currency': currency,
            'updatedAt': fetched_at, 'provider': '东方财富前复权日线', 'adjustment': 'forward',
            'source': 'https://quote.eastmoney.com/hk/' + code + '.html',
            'bars': sorted({bar['date']: bar for bar in bars}.values(), key=lambda bar: bar['date'])}


def refresh_history(code):
    item = stock(code)
    if not item:
        raise LookupError('Unknown constituent')
    currency = item.get('currency', 'HKD')
    try:
        query = {'secid': '116.' + code, 'klt': '101', 'fqt': '1', 'lmt': '320', 'end': '20500101',
                 'fields1': 'f1,f2,f3,f4,f5,f6', 'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61'}
        payload = json.loads(request('https://push2his.eastmoney.com/api/qt/stock/kline/get?' + urllib.parse.urlencode(query)))
        result = normalize_em_history(payload, code, currency, now())
    except (OSError, ValueError, KeyError, TypeError):
        symbol = str(int(code)).zfill(4) + '.HK'
        result = normalize_chart(chart(symbol), now())
    if result.get('currency') != currency or not result['bars']:
        raise ValueError('Invalid HK price history')
    result['code'] = code
    publish(FOLDER / 'history' / (code + '.json'), result)
    return result


def em_report(code, report, columns='ALL', extra_filter='', page_size=500):
    rows = []
    for page in range(1, 11):
        query = {'reportName': report, 'columns': columns, 'filter': '(SECUCODE="' + code + '.HK")' + extra_filter,
                 'pageNumber': page, 'pageSize': page_size, 'source': 'F10', 'client': 'PC'}
        payload = json.loads(request(EASTMONEY + '?' + urllib.parse.urlencode(query)))
        if not payload.get('success'):
            raise ValueError('Company source returned no valid report')
        result = payload.get('result') or {}
        data = result.get('data') or []
        if not isinstance(data, list):
            raise ValueError('Invalid company data')
        identity_rows = [item for row in data for item in (row.get('REPORT_LIST') or [row])]
        if any(row.get('SECUCODE') != code + '.HK' for row in identity_rows):
            raise ValueError('Company identity mismatch')
        rows.extend(data)
        pages = int(result.get('pages') or 1)
        if pages <= page:
            return rows
        if pages > 10:
            raise ValueError('Company report exceeds pagination limit')
    raise ValueError('Incomplete company report')


def refresh_company(code):
    item = stock(code)
    if not item:
        raise LookupError('Unknown constituent')
    path = FOLDER / 'companies' / (code + '.json')
    old = load(path)
    result = {**old, **item, 'version': 1, 'checkedAt': now(), 'failedSections': [],
              'source': 'https://emweb.securities.eastmoney.com/PC_HKF10/pages/home/index.html?code=' + code + '&type=web&color=w',
              'sourceLabel': '东方财富港股资料', 'officialFilings': 'https://www.hkexnews.hk/'}
    try:
        profile = em_report(code, 'RPT_HKF10_INFO_ORGPROFILE')[0]
        fields = {'ORG_NAME': 'legalName', 'BELONG_INDUSTRY': 'industry', 'LISTING_DATE': 'listedAt',
                  'FOUND_DATE': 'foundedAt', 'CHAIRMAN': 'chairman', 'REG_PLACE': 'registeredAt',
                  'EMP_NUM': 'employees', 'ORG_WEB': 'website', 'MAIN_BUSINESS': 'business'}
        result['profile'] = {value: profile.get(key) for key, value in fields.items()}
        result['profile']['updatedAt'] = now()
    except (OSError, ValueError, IndexError, KeyError):
        result['failedSections'].append('profile')
    try:
        holders = em_report(code, 'RPT_HKF10_EQUITYCHG_HOLDER',
            'SECUCODE,SECURITY_CODE,NOTICE_DATE,REPORT_DATE,HOLDER_NAME,TOTAL_SHARES,TOTAL_SHARES_RATIO,DIRECT_SHARES,SHARES_TYPE,EQUITY_TYPE,HOLD_IDENTITY,IS_ZJ',
            '(@REPORT_DATE=max(SECUCODE="' + code + '.HK"))')
        result['holders'] = {'updatedAt': now(), 'rows': [
            {'name': row.get('HOLDER_NAME'), 'shares': number(row.get('TOTAL_SHARES')),
             'percentage': number(row.get('TOTAL_SHARES_RATIO')), 'directShares': number(row.get('DIRECT_SHARES')),
             'shareClass': row.get('SHARES_TYPE'), 'identity': row.get('EQUITY_TYPE'), 'basis': row.get('HOLD_IDENTITY'),
             'asOf': row.get('REPORT_DATE'), 'announcedAt': row.get('NOTICE_DATE')}
            for row in sorted(holders, key=lambda r: -(number(r.get('TOTAL_SHARES')) or 0))]}
    except (OSError, ValueError, KeyError):
        result['failedSections'].append('holders')
    try:
        reports = em_report(code, 'RPT_CUSTOM_HKSK_APPFN_CASHFLOW_SUMMARY',
            'SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,START_DATE,REPORT_DATE,FISCAL_YEAR,CURRENCY,ACCOUNT_STANDARD,REPORT_TYPE')
        periods = sorted(reports[0]['REPORT_LIST'], key=lambda r: r['REPORT_DATE'], reverse=True)[:6]
        by_date = {p['REPORT_DATE'][:10]: p for p in periods}
        dates = ','.join("'" + date + "'" for date in by_date)
        if not dates:
            raise ValueError('Financial periods unavailable')
        financials = {'updatedAt': now(), 'periods': periods, 'statements': {}, 'amountCurrency': 'CNY',
                      'currencyBasis': '东方财富统一折算人民币；报告原币种另存。'}
        for kind, report in [('balance', 'RPT_HKF10_FN_BALANCE_PC'), ('income', 'RPT_HKF10_FN_INCOME_PC'), ('cashflow', 'RPT_HKF10_FN_CASHFLOW_PC')]:
            items = em_report(code, report, extra_filter='(REPORT_DATE in (' + dates + '))')
            financials['statements'][kind] = [
                {'code': row.get('STD_ITEM_CODE'), 'name': row.get('STD_ITEM_NAME'), 'amount': number(row.get('AMOUNT')),
                 'date': row['REPORT_DATE'][:10], 'startDate': row.get('START_DATE'),
                 'currency': '人民币', 'reportCurrency': by_date.get(row['REPORT_DATE'][:10], {}).get('CURRENCY'),
                 'reportType': by_date.get(row['REPORT_DATE'][:10], {}).get('REPORT_TYPE')}
                for row in items if row.get('REPORT_DATE', '')[:10] in by_date]
        result['financials'] = financials
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        result['failedSections'].append('financials')
    try:
        from .company_leaders import refresh_leaders
        result['leadership'] = refresh_leaders(code, result.get('profile', {}).get('chairman'))
    except (OSError, ValueError, KeyError, TypeError):
        result['failedSections'].append('leadership')
    if not any(result.get(key) for key in ['profile', 'holders', 'financials']):
        raise OSError('Company information unavailable')
    publish(path, result)
    from .capital_structure import update_capital_index
    update_capital_index(result)
    return result


def refresh_collection(kind):
    action = refresh_company if kind == 'companies' else refresh_history
    def one(item):
        try:
            action(item['code'])
            return item['code'], True
        except (OSError, ValueError, KeyError, TypeError):
            return item['code'], False
    items = {row['code']: row for row in constituents()}
    if kind == 'history':
        for path in (FOLDER / 'history').glob('*.json'):
            item = stock(path.stem)
            if item:
                items[item['code']] = item
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(one, items.values()))
    good = sum(ok for _, ok in rows)
    result = {'updatedAt': now(), 'total': len(rows), 'ok': good, 'failedCodes': [code for code, ok in rows if not ok]}
    publish(FOLDER / (kind + '-status.json'), result)
    if not good:
        raise OSError('All market source checks failed')
    return result
