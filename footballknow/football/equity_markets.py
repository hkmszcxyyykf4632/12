"""Shanghai and Shenzhen shares, with shared stock-detail contracts."""
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

from .finance import FOLDER, EASTMONEY, load, now, number, request, normalize_em_history, normalize_chart, chart
from .files import publish

SCAN_COLUMNS = ['name', 'description', 'sector', 'industry', 'exchange', 'type', 'currency',
                'close', 'change', 'change_abs', 'open', 'high', 'low', 'volume',
                'average_volume_10d_calc', 'average_volume_30d_calc', 'average_volume_60d_calc',
                'average_volume_90d_calc', 'update_mode', 'time', 'price_52_week_high', 'price_52_week_low']
SECTORS = {'Technology Services': '科技', 'Electronic Technology': '科技', 'Finance': '金融',
           'Health Technology': '医疗保健', 'Health Services': '医疗保健', 'Energy Minerals': '能源资源',
           'Non-Energy Minerals': '能源资源', 'Consumer Durables': '消费', 'Consumer Non-Durables': '消费',
           'Retail Trade': '消费', 'Consumer Services': '消费服务', 'Transportation': '交通运输',
           'Utilities': '电讯公用', 'Communications': '电讯公用', 'Producer Manufacturing': '工业制造',
           'Process Industries': '工业制造', 'Industrial Services': '建筑工程', 'Distribution Services': '商业服务',
           'Commercial Services': '商业服务', 'Miscellaneous': '其他'}


def scan(region, body):
    body = {**body, 'options': {'lang': 'zh'}, 'columns': SCAN_COLUMNS}
    req = urllib.request.Request('https://scanner.tradingview.com/' + region + '/scan',
        data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'User-Agent': 'FootballKnow/3.0 (+https://inwesting.shop)'})
    with urllib.request.urlopen(req, timeout=25) as response:
        raw = response.read(8_000_001)
    if len(raw) > 8_000_000:
        raise ValueError('Stock scan exceeds limit')
    return json.loads(raw)


def scan_rows(payload):
    rows = payload.get('data')
    if not isinstance(rows, list):
        raise ValueError('Invalid stock scan')
    return [(r.get('s'), dict(zip(SCAN_COLUMNS, r['d']))) for r in rows if isinstance(r, dict) and len(r.get('d', [])) == len(SCAN_COLUMNS)]


def sector_for(raw):
    if raw.get('industry') in {'Real Estate Development', 'Real Estate Investment Trusts'}:
        return '地产'
    return SECTORS.get(raw.get('sector'), '待分类')


def quote_from_scan(code, symbol, raw, stamp, currency):
    price = number(raw.get('close'), True)
    epoch = number(raw.get('time'), True)
    if price is None or raw.get('currency') != currency or not epoch:
        return None
    bar_at = datetime.fromtimestamp(epoch, timezone.utc)
    if bar_at > datetime.fromisoformat(stamp) + timedelta(minutes=5):
        return None
    delay = re.fullmatch(r'delayed_streaming_(\d+)', str(raw.get('update_mode')))
    return {'code': code, 'name': raw.get('description'), 'price': price, 'currency': currency,
            'changePercent': number(raw.get('change')), 'change': number(raw.get('change_abs')),
            'open': number(raw.get('open')), 'high': number(raw.get('high')), 'low': number(raw.get('low')),
            'volume': number(raw.get('volume')), 'volumeUnit': '股',
            'high52': number(raw.get('price_52_week_high'), True), 'low52': number(raw.get('price_52_week_low'), True),
            'quotedAt': None, 'barAt': bar_at.isoformat(), 'fetchedAt': stamp,
            'delaySeconds': int(delay[1]) if delay else None, 'updateMode': raw.get('update_mode'),
            'provider': 'TradingView', 'source': 'https://www.tradingview.com/symbols/' + symbol.replace(':', '-') + '/',
            'timeliness': '参考行情；显示采集时间及来源延迟，日线时间不是逐笔成交时间'}


def refresh_cn():
    stamp = now()
    payload = scan('china', {'filter': [{'left': 'type', 'operation': 'equal', 'right': 'stock'},
        {'left': 'currency', 'operation': 'equal', 'right': 'CNY'}], 'range': [0, 10000],
        'sort': {'sortBy': 'name', 'sortOrder': 'asc'}})
    parsed = scan_rows(payload)
    if not isinstance(payload.get('totalCount'), int) or len(parsed) != payload['totalCount'] or not 3000 <= len(parsed) < 10000:
        raise ValueError('Incomplete China equity catalogue; previous catalogue retained')
    rows, quotes, volumes = [], {}, []
    for symbol, raw in parsed:
        exchange, _, code = str(symbol).partition(':')
        if exchange not in {'SSE', 'SZSE'} or not re.fullmatch(r'\d{6}', code) or raw.get('name') != code or raw.get('currency') != 'CNY':
            continue
        if raw.get('type') != 'stock' or raw.get('exchange') != exchange or code[0] not in '036':
            continue
        board = '科创板' if code.startswith('688') else '创业板' if code.startswith('30') else '沪市主板' if exchange == 'SSE' else '深市主板'
        rows.append({'code': code, 'name': raw['description'], 'market': 'cn', 'exchange': exchange,
            'symbol': symbol, 'currency': 'CNY', 'board': board, 'industry': raw.get('industry'),
            'sector': sector_for(raw), 'industryUpdatedAt': stamp, 'securityType': 'A股', 'isHsi': False})
        quote = quote_from_scan(code, symbol, raw, stamp, 'CNY')
        if quote:
            quotes[code] = quote
        volumes.append({'code': code, 'market': 'cn', 'symbol': symbol, 'raw': raw})
    if len(rows) < 3000 or len({r['code'] for r in rows}) != len(rows):
        raise ValueError('Invalid Shanghai/Shenzhen equity coverage')
    catalogue = {'version': 1, 'updatedAt': stamp, 'effectiveDate': stamp[:10], 'stocks': rows,
        'source': 'https://www.tradingview.com/markets/stocks-china/market-movers-all-stocks/',
        'sourceLabel': 'TradingView 沪深股票目录', 'scope': '上海、深圳人民币 A 股；不包括北交所、B 股、基金与债券。',
        'industryUpdatedAt': stamp, 'industryCoverage': sum(r['sector'] != '待分类' for r in rows),
        'industrySource': 'https://www.tradingview.com/markets/stocks-china/sectorandindustry-sector/', 'industrySourceLabel': 'TradingView 行业分类'}
    publish(FOLDER / 'cn-stocks.json', catalogue)
    previous = load(FOLDER / 'cn-quotes.json').get('quotes', {})
    publish(FOLDER / 'cn-quotes.json', {'version': 1, 'updatedAt': stamp, 'quotes': {**previous, **quotes},
        'failedCodes': [r['code'] for r in rows if r['code'] not in quotes]})
    publish(FOLDER / 'cn-volume-source.json', {'updatedAt': stamp, 'rows': volumes})
    return {'stocks': len(rows), 'quotes': len(quotes)}


def refresh_cn_history(item):
    code, exchange = item['code'], item['exchange']
    try:
        params = {'secid': ('1.' if exchange == 'SSE' else '0.') + code, 'klt': 101, 'fqt': 1,
            'lmt': 320, 'end': '20500101', 'fields1': 'f1,f2,f3,f4,f5,f6', 'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61'}
        payload = json.loads(request('https://push2his.eastmoney.com/api/qt/stock/kline/get?' + urllib.parse.urlencode(params)))
        result = normalize_em_history(payload, code, 'CNY', now())
        result.update(symbol=code + ('.SS' if exchange == 'SSE' else '.SZ'), volumeUnit='手（100股）',
                      source='https://quote.eastmoney.com/' + ('sh' if exchange == 'SSE' else 'sz') + code + '.html')
    except (OSError, ValueError, KeyError, TypeError):
        result = normalize_chart(chart(code + ('.SS' if exchange == 'SSE' else '.SZ')), now())
        result['volumeUnit'] = '股'
    if result.get('currency') != 'CNY' or not result.get('bars'):
        raise ValueError('Invalid CNY history')
    result.update(code=code, market='cn')
    publish(FOLDER / 'history' / (code + '.json'), result)
    return result


FINANCIAL_FIELDS = {
    'balance': {'TOTAL_ASSETS': '资产总额', 'MONETARYFUNDS': '货币资金', 'ACCOUNTS_RECE': '应收账款',
        'INVENTORY': '存货', 'FIXED_ASSET': '固定资产', 'TOTAL_LIABILITIES': '负债总额',
        'ACCOUNTS_PAYABLE': '应付账款', 'TOTAL_EQUITY': '所有者权益', 'SHORT_LOAN': '短期借款'},
    'income': {'TOTAL_OPERATE_INCOME': '营业总收入', 'OPERATE_INCOME': '营业收入', 'TOTAL_OPERATE_COST': '营业总成本',
        'OPERATE_COST': '营业成本', 'SALE_EXPENSE': '销售费用', 'MANAGE_EXPENSE': '管理费用', 'FINANCE_EXPENSE': '财务费用',
        'OPERATE_PROFIT': '营业利润', 'TOTAL_PROFIT': '利润总额', 'PARENT_NETPROFIT': '归母净利润', 'DEDUCT_PARENT_NETPROFIT': '扣非归母净利润'},
    'cashflow': {'NETCASH_OPERATE': '经营活动现金流量净额', 'NETCASH_INVEST': '投资活动现金流量净额',
        'NETCASH_FINANCE': '筹资活动现金流量净额', 'SALES_SERVICES': '销售商品提供劳务收到的现金',
        'BEGIN_CCE': '期初现金及现金等价物', 'END_CCE': '期末现金及现金等价物', 'CCE_ADD': '现金及现金等价物净增加额'}}


def checked_rows(rows, identity):
    if not isinstance(rows, list) or not rows or any(r.get('SECUCODE') != identity for r in rows):
        raise ValueError('Company identity mismatch')
    return rows


def refresh_cn_company(item):
    code = item['code']
    suffix = 'SH' if item['exchange'] == 'SSE' else 'SZ'
    identity = code + '.' + suffix
    url = 'https://emweb.securities.eastmoney.com/PC_HSF10/'
    old = load(FOLDER / 'companies' / (code + '.json'))
    result = {**old, **item, 'version': 1, 'checkedAt': now(), 'failedSections': [],
        'source': 'https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/Index?type=web&code=' + suffix + code,
        'sourceLabel': '东方财富沪深公司资料', 'officialFilings': 'https://www.cninfo.com.cn/', 'filingsLabel': '巨潮资讯公告'}
    try:
        data = json.loads(request(url + 'CompanySurvey/PageAjax?code=' + suffix + code))
        p = checked_rows(data.get('jbzl'), identity)[0]
        result['profile'] = {'legalName': p.get('ORG_NAME'), 'business': p.get('BUSINESS_SCOPE'),
            'industry': p.get('EM2016'), 'chairman': p.get('CHAIRMAN'), 'registeredAt': p.get('REG_ADDRESS'),
            'employees': p.get('EMP_NUM'), 'website': p.get('ORG_WEB'), 'updatedAt': now()}
    except (OSError, ValueError, KeyError, TypeError):
        result['failedSections'].append('profile')
    try:
        data = json.loads(request(url + 'ShareholderResearch/PageAjax?code=' + suffix + code))
        rows = checked_rows(data.get('sdgd'), identity)
        latest = max(str(r.get('END_DATE') or '') for r in rows)
        result['holders'] = {'updatedAt': now(), 'rows': [{'name': r.get('HOLDER_NAME'), 'shares': number(r.get('HOLD_NUM')),
            'percentage': number(r.get('HOLD_NUM_RATIO')), 'shareClass': r.get('SHARES_TYPE'), 'asOf': r.get('END_DATE')}
            for r in rows if r.get('END_DATE') == latest]}
    except (OSError, ValueError, KeyError, TypeError):
        result['failedSections'].append('holders')
    financials = {'updatedAt': now(), 'periods': [], 'statements': {}, 'amountCurrency': 'CNY', 'currencyBasis': '来源人民币报表，金额为元。'}
    periods = {}
    for kind, fields in FINANCIAL_FIELDS.items():
        try:
            query = {'reportName': 'RPT_DMSK_FN_' + kind.upper(), 'columns': 'ALL',
                'filter': '(SECUCODE="' + identity + '")', 'pageNumber': 1, 'pageSize': 6,
                'sortColumns': 'REPORT_DATE', 'sortTypes': -1}
            data = json.loads(request(EASTMONEY + '?' + urllib.parse.urlencode(query)))
            rows = checked_rows((data.get('result') or {}).get('data'), identity)
            output = []
            for r in rows:
                day = str(r.get('REPORT_DATE') or '')[:10]
                datetime.strptime(day, '%Y-%m-%d')
                report_type = {'03-31': '一季报', '06-30': '中报', '09-30': '三季报', '12-31': '年报'}.get(day[5:], '定期报告')
                periods[day] = {'REPORT_DATE': day, 'REPORT_TYPE': report_type}
                output.extend({'code': key, 'name': label, 'amount': number(r.get(key)), 'date': day,
                    'currency': '人民币', 'reportCurrency': 'CNY', 'reportType': report_type}
                    for key, label in fields.items())
            financials['statements'][kind] = output
        except (OSError, ValueError, KeyError, TypeError):
            result['failedSections'].append(kind)
            financials['statements'][kind] = old.get('financials', {}).get('statements', {}).get(kind, [])
    if periods:
        financials['periods'] = [periods[d] for d in sorted(periods, reverse=True)]
        result['financials'] = financials
    if not result.get('profile'):
        raise OSError('Company profile unavailable')
    publish(FOLDER / 'companies' / (code + '.json'), result)
    return result
