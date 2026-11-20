"""A deliberately small reference list; regular-session quotes and on-demand charts."""
import threading
from datetime import datetime, timezone, timedelta
from .equity_markets import scan, scan_rows, quote_from_scan
from .finance import FOLDER, now, load, chart, normalize_chart
from .files import publish
from .sync_control import read_control

COMPANIES = [
    ('AAPL', 'NASDAQ', '苹果', '科技', 'iPhone、Mac 等消费电子产品及数字服务。', 'https://www.apple.com/'),
    ('MSFT', 'NASDAQ', '微软', '科技', '企业软件、Azure 云服务、办公工具与游戏业务。', 'https://www.microsoft.com/en-us/investor/'),
    ('NVDA', 'NASDAQ', '英伟达', '科技', '图形处理器、加速计算与人工智能计算平台。', 'https://www.nvidia.com/'),
    ('GOOGL', 'NASDAQ', '谷歌 Alphabet', '科技', 'Google 搜索、广告、YouTube 与云服务。', 'https://abc.xyz/'),
    ('AMZN', 'NASDAQ', '亚马逊', '消费 / 科技', '电子商务、物流、AWS 云服务及数字内容。', 'https://ir.aboutamazon.com/'),
    ('META', 'NASDAQ', 'Meta', '科技', 'Facebook、Instagram、WhatsApp 等社交产品与广告。', 'https://investor.atmeta.com/'),
    ('TSLA', 'NASDAQ', '特斯拉', '汽车 / 能源', '电动汽车、储能与能源产品。', 'https://ir.tesla.com/'),
    ('BRK.B', 'NYSE', '伯克希尔 B 股', '金融 / 综合', '保险及多行业经营业务和上市证券投资。', 'https://www.berkshirehathaway.com/'),
    ('JPM', 'NYSE', '摩根大通', '金融', '商业银行、投资银行、支付与资产管理。', 'https://www.jpmorganchase.com/ir'),
    ('XOM', 'NYSE', '埃克森美孚', '能源', '石油与天然气开发、炼化和化工产品。', 'https://corporate.exxonmobil.com/')]
DEFINITIONS = {ticker: {'ticker': ticker, 'symbol': exchange + ':' + ticker, 'exchange': exchange,
    'name': name, 'sector': sector, 'business': business, 'website': website, 'currency': 'USD'}
    for ticker, exchange, name, sector, business, website in COMPANIES}
LOCK = threading.Lock()


def refresh_us():
    stamp = now()
    previous = load(FOLDER / 'us-reference.json')
    old = {r['ticker']: r for r in previous.get('stocks', [])}
    payload = scan('america', {'symbols': {'tickers': [r['symbol'] for r in DEFINITIONS.values()], 'query': {'types': []}}})
    fresh = {}
    for symbol, raw in scan_rows(payload):
        ticker = str(symbol).partition(':')[2]
        item = DEFINITIONS.get(ticker)
        if item and item['symbol'] == symbol and raw.get('name') == ticker and raw.get('type') == 'stock':
            q = quote_from_scan(ticker, symbol, raw, stamp, 'USD')
            if q:
                fresh[ticker] = q
    if not fresh:
        raise OSError('US reference quotes unavailable')
    rows = [{**item, 'quote': fresh.get(ticker) or old.get(ticker, {}).get('quote'), 'lastCheckOk': ticker in fresh}
            for ticker, item in DEFINITIONS.items()]
    result = {'version': 1, 'updatedAt': stamp, 'stocks': rows,
        'scope': '10 家知名公司，供跨市场参考。常规时段行情与盘前盘后交易分开；本区不合并盘前盘后报价。',
        'failedTickers': [ticker for ticker in DEFINITIONS if ticker not in fresh]}
    publish(FOLDER / 'us-reference.json', result)
    return {'quotes': len(fresh), 'selected': len(rows)}


def history(ticker):
    if ticker not in DEFINITIONS:
        raise LookupError('不在精选美股名单中')
    path = FOLDER / 'us-history' / (ticker + '.json')
    old = load(path)
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(old.get('updatedAt', ''))).total_seconds()
    except ValueError:
        age = float('inf')
    if age < 3600 or not read_control()['enabled']:
        return {**old, 'paused': not read_control()['enabled']}
    if not LOCK.acquire(blocking=False):
        return {**old, 'pending': True}
    try:
        raw = chart(ticker.replace('.', '-'))
        result = normalize_chart(raw, now())
        if result.get('currency') != 'USD' or not result.get('bars'):
            raise ValueError('Invalid USD history')
        offset = raw.get('meta', {}).get('gmtoffset')
        if not isinstance(offset, (int, float)) or not -21600 <= offset <= -10800:
            raise ValueError('US exchange timezone unavailable')
        for bar in result['bars']:
            bar['date'] = datetime.fromisoformat(bar['timestamp']).astimezone(timezone(timedelta(seconds=offset))).date().isoformat()
        result.update(ticker=ticker, volumeUnit='股')
        publish(path, result)
        return result
    except (OSError, ValueError, TypeError, KeyError):
        return {**old, 'message': '历史价格暂未更新，保留上次资料。'}
    finally:
        LOCK.release()
