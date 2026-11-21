"""Pure, dated price evidence for a saved stock forecast; no causal inference."""
import math
from datetime import date, datetime, timedelta, timezone

from .evidence_reviews import add_fact, add_source, new_dossier


HK = timezone(timedelta(hours=8))
HORIZONS = (('week', 5, .01, '短期'), ('quarter', 63, .05, '中期'))


def _number(value, positive=False):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and (value > 0 if positive else value >= 0))


def _day(value):
    try:
        normalized = date.fromisoformat(value).isoformat()
        return normalized if normalized == value else None
    except (TypeError, ValueError):
        return None


def _identity(code, original, history, result):
    for item in (original, history, result):
        if item.get('code') is not None and str(item['code']) != code:
            raise ValueError('Stock evidence identity mismatch')
    symbol = history.get('symbol')
    if symbol:
        symbol_code = str(symbol).split(':')[-1].split('.')[0]
        if not symbol_code.isdigit() or symbol_code.zfill(len(code)) != code:
            raise ValueError('Stock evidence symbol mismatch')


def build_dossier(code, original, history, closed_bars, result):
    """Use confirmed bars only; baseline is first close after the HK issue date."""
    _identity(code, original, history, result)
    try:
        issued = datetime.fromisoformat(original['issuedAt'].replace('Z', '+00:00'))
        if issued.tzinfo is None:
            raise ValueError('Missing timezone')
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Stock forecast requires a timezone-aware issue time') from exc
    issued_day = issued.astimezone(HK).date().isoformat()
    end = _day((result.get('close') or {}).get('date'))
    if not end or end < issued_day:
        raise ValueError('Stock evidence requires a confirmed close date')
    identity = f"{code}|{end}|{original.get('id')}"
    dossier = new_dossier('stocks', identity, original)
    gaps = dossier['gaps']
    source = add_source(dossier, history.get('source') or '',
                        history.get('provider') or '保存的个股日线', history.get('updatedAt'))
    if not history.get('source'):
        gaps.append('日线缺少可回查来源网址。')
    if not history.get('updatedAt'):
        gaps.append('日线缺少抓取更新时间，不能确认来源新鲜度。')
    if not history.get('code') and not history.get('symbol'):
        gaps.append('历史行情未提供独立证券标识，仅由调用方的股票代码绑定。')
    gaps.extend([
        '缺少同区间、同币种与可比复权口径的基准指数历史，不能计算超额收益或判断是否仅随大盘。',
        '缺少绑定该公司、带首次公开时间及原始链接的公告与新闻资料，不能判定消息在预测前被遗漏还是预测后的突发事件；不能把新闻标题当成价格变化原因。',
        '来源 updatedAt 仅为行情抓取时间；日线日期为交易日，均不是公告首次公开时间或财报公开时间。',
        '缺少交易所日历及停牌记录，日期间隔不能直接认定为缺失交易日；缺失价格可能使交易日到期计算延后。',
    ])
    valid = {}
    invalid = 0
    duplicates = set()
    for bar in closed_bars:
        day = _day(bar.get('date'))
        if not day or not _number(bar.get('adjustedClose'), positive=True):
            invalid += 1
            continue
        if day > end:
            continue
        if day in valid:
            duplicates.add(day)
        valid[day] = bar
    if duplicates:
        raise ValueError('Duplicate confirmed stock trading dates')
    if invalid:
        gaps.append(f'已确认日线中有 {invalid} 条日期或复权收盘无效，未用于价格计算。')
    missing_prices = [bar for bar in history.get('bars', [])
                      if _day(bar.get('date')) and issued_day < bar['date'] <= end
                      and not _number(bar.get('adjustedClose'), positive=True)]
    if missing_prices:
        gaps.append(f'源历史中发布后有 {len(missing_prices)} 条日线缺少有效复权收盘，未补值，观察及到期进度可能不完整。')
    confirmed = [valid[day] for day in sorted(valid)]
    bars = [bar for bar in confirmed if bar['date'] > issued_day]
    unit = history.get('volumeUnit') or '未知（来源未说明）'
    if not history.get('volumeUnit'):
        gaps.append('成交量单位未知，不能换算为股数或成交金额；同来源同口径比值仅供观察。')
    dossier['priceContext'] = context = {
        'code': code, 'issuedAt': original['issuedAt'], 'issuedDay': issued_day,
        'asOf': end, 'sourceUpdatedAt': history.get('updatedAt'),
        'currency': history.get('currency'), 'adjustment': history.get('adjustment'),
        'volumeUnit': unit, 'baselineDate': bars[0]['date'] if bars else None,
        'completedSessions': max(0, len(bars) - 1), 'path': [], 'horizons': {},
        'periodReturn': None, 'maxDrawdown': None,
    }
    add_fact(dossier,
        '收益均使用 adjustedClose。基准是预测发布日之后首个交易日收盘；基准之后第5/63个交易日分别评估短期/中期，涨跌阈值为±1%/±5%，边界归横盘。区间收益和单日涨跌仅为观察，不代表提前到期。',
        [source], category='method', time=end)
    dossier['overview'].append('只比较保存的原预测与截至已确认收盘的证据；方向错误不自动证明原理由错误。')
    if not bars:
        gaps.append('发布日之后尚无可用的已确认复权收盘，不能建立预测评估基准。')
        return dossier
    if bars[-1]['date'] != end:
        gaps.append('目标收盘日缺少有效复权价格，价格路径仅覆盖最后可用日。')
    first = bars[0]['adjustedClose']
    peak, max_drawdown = first, 0
    for bar in bars:
        day, close = bar['date'], bar['adjustedClose']
        prior = [entry for entry in confirmed if entry['date'] < day]
        previous = prior[-1]['adjustedClose'] if prior else None
        change = close / previous - 1 if previous else None
        peak = max(peak, close)
        drawdown = close / peak - 1
        max_drawdown = min(max_drawdown, drawdown)
        volumes = [entry.get('volume') for entry in prior[-20:]]
        volume = bar.get('volume') if _number(bar.get('volume')) else None
        volume_mean = (sum(volumes) / 20 if len(volumes) == 20
                       and all(_number(v) for v in volumes) else None)
        ratio = volume / volume_mean if volume is not None and volume_mean and volume_mean > 0 else None
        row = {'date': day, 'adjustedClose': close, 'dailyReturn': change,
               'drawdownFromPeak': drawdown, 'volume': volume, 'volumeUnit': unit,
               'prior20VolumeAverage': volume_mean, 'volumeRatioToPrior20': ratio,
               'sourceOHLC': {k: bar.get(k) if _number(bar.get(k), positive=True) else None
                              for k in ('open', 'high', 'low', 'close')}}
        context['path'].append(row)
        daily = f'较前一可用收盘 {change:+.2%}' if change is not None else '缺少前一可用收盘，单日变化未知'
        volume_text = f'成交量 {volume:g}，单位：{unit}' if volume is not None else '成交量缺失或无效'
        volume_text += (f'；相对此前20条有效日线均量 {ratio:.2f} 倍（不含当日）'
                        if ratio is not None else '；此前20条日线均量比值不可计算')
        fact = add_fact(dossier, f'{day} 复权收盘 {close:g}；{daily}；{volume_text}。',
                        [source], time=day, before_event=False)
        dossier['timeline'].append({'time': day, 'text': f'收盘 {close:g}；{daily}', 'evidenceIds': [fact]})
    context['periodReturn'] = bars[-1]['adjustedClose'] / first - 1
    context['maxDrawdown'] = max_drawdown
    add_fact(dossier, f"基准 {bars[0]['date']} 复权收盘 {first:g}，截至 {bars[-1]['date']} 共经过 {len(bars)-1} 个可用交易日间隔，区间收益 {context['periodReturn']:+.2%}，收盘路径最大回撤 {max_drawdown:.2%}；未包含盘中回撤。",
             [source], time=bars[-1]['date'], before_event=False)
    add_fact(dossier, '原始 OHLC 仅按来源原值保存；未把 adjustedClose 与 OHLC 拼成复权蜡烛图，未据此推断盘中支撑、突破或最高最低收益。',
             [source], category='method', time=end)
    for horizon, sessions, threshold, label in HORIZONS:
        ready = len(bars) > sessions
        value = bars[sessions]['adjustedClose'] / first - 1 if ready else None
        actual = ('up' if value > threshold else 'down' if value < -threshold else 'flat') if ready else None
        prediction = original.get(horizon)
        outcome = {'prediction': prediction, 'requiredSessions': sessions, 'threshold': threshold,
                   'status': '已到期' if ready else '观察中', 'return': value, 'actual': actual,
                   'correct': prediction == actual if ready and prediction in ('up', 'down', 'flat') else None,
                   'baseDate': bars[0]['date'], 'targetDate': bars[sessions]['date'] if ready else None}
        context['horizons'][horizon] = outcome
        text = (f"{label}原方向 {prediction}；第{sessions}个交易日 {outcome['targetDate']} 收益 {value:+.2%}，实际 {actual}，方向{'吻合' if outcome['correct'] else '不吻合'}。"
                if ready and outcome['correct'] is not None else
                f'{label}原方向 {prediction}；观察中，基准后需满{sessions}个交易日，不能用当前涨跌判定成功或失败。')
        add_fact(dossier, text, [source], category='outcome', time=outcome['targetDate'] or end, before_event=False)
    return dossier
