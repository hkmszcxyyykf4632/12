"""Cached futures charts with reproducible technical context."""
import math
import statistics
import threading
from datetime import datetime, timezone
from .finance import FOLDER, chart, normalize_chart, load, now
from .files import publish
from .sync_control import read_control

INSTRUMENTS = {'gold': ('GC=F', '黄金', '美元/金衡盎司'), 'silver': ('SI=F', '白银', '美元/金衡盎司'),
               'platinum': ('PL=F', '铂金', '美元/金衡盎司'), 'palladium': ('PA=F', '钯金', '美元/金衡盎司'),
               'wti': ('CL=F', 'WTI原油', '美元/桶'), 'brent': ('BZ=F', '布伦特原油', '美元/桶')}
LOCK = threading.Lock()


def technical(bars):
    rows = sorted({r['date']: r for r in bars if isinstance(r.get('close'), (int, float)) and math.isfinite(r['close']) and r['close'] > 0}.values(), key=lambda r: r['date'])
    if len(rows) < 20:
        return {'summary': '日线少于20根，暂不计算趋势和区间波动。', 'count': len(rows)}
    closes = [r['close'] for r in rows]
    ma5, ma10, ma20 = [statistics.mean(closes[-n:]) for n in [5, 10, 20]]
    price = closes[-1]
    trend = '短期偏强' if price > ma5 > ma10 > ma20 else '短期偏弱' if price < ma5 < ma10 < ma20 else '均线交错'
    returns = [math.log(b/a) for a, b in zip(closes[-21:-1], closes[-20:])]
    volatility = statistics.stdev(returns) * math.sqrt(252) * 100 if len(closes) >= 21 else None
    high, low = max(closes[-20:]), min(closes[-20:])
    return {'summary': f'最近日线收盘{price:.2f}，5/10/20日均线分别为{ma5:.2f}/{ma10:.2f}/{ma20:.2f}，当前属于{trend}。',
        'context': f'近20日收盘区间为{low:.2f}—{high:.2f}；后续是否持续站稳区间上沿或跌破下沿，需要用新收盘数据验证。',
        'ma5': ma5, 'ma10': ma10, 'ma20': ma20, 'volatility20Annualized': volatility,
        'asOf': rows[-1]['date'], 'count': len(rows), 'trend': trend,
        'method': '均线为收盘价简单平均；波动率为最近20个对数日收益的样本标准差×√252。连续期货换月可能影响图形；最新日线在收盘前仍会变化。'}


def history(ident):
    if ident not in INSTRUMENTS:
        raise LookupError('未知贵金属或原油品种')
    path = FOLDER / 'commodity-history' / (ident + '.json')
    old = load(path)
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(old.get('updatedAt', ''))).total_seconds()
    except ValueError:
        age = float('inf')
    if 0 <= age < 3600 or not read_control()['enabled']:
        return {**old, 'paused': not read_control()['enabled']}
    if not LOCK.acquire(blocking=False):
        return {**old, 'pending': True}
    try:
        symbol, name, unit = INSTRUMENTS[ident]
        raw = chart(symbol)
        if raw.get('meta', {}).get('symbol') != symbol:
            raise ValueError('Futures symbol mismatch')
        result = normalize_chart(raw, now())
        if result.get('currency') != 'USD' or not result.get('bars'):
            raise ValueError('Futures currency or bars missing')
        result.update(id=ident, name=name, unit=unit, volumeUnit='张', analysis=technical(result['bars']),
                      basis='Yahoo Finance 连续期货日线；右侧图表和报价表来源独立，不拼接报价作为日线。')
        publish(path, result)
        return result
    except (OSError, ValueError, TypeError, KeyError):
        return {**old, 'message': '历史行情暂未更新，保留已保存数据。'}
    finally:
        LOCK.release()
