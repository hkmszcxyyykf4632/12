"""Deterministic, versioned odds-movement trial; no text-generation service calls."""
import math
from datetime import timedelta

from .odds_signals import LABELS, VERSION, profit, valid_quote
from .motivation import dt


def describe(change):
    before, after = change['before'], change['after']
    basis = {'opening': '来源开盘', 'first-observed': '本站首次记录',
             'same-opponent-same-venue': '上次同对手同主客场收盘'}[change['basis']]
    if change['lineChange']:
        return f"{after['provider']}的{LABELS[after['market']]}由{basis}{before['line']:+g}变为{after['line']:+g}"
    side = change['side']
    delta = change['weightChangesPP'][side]
    return (f"{after['provider']}的{LABELS[after['market']]}盘口不变，{side}项赔率"
            f"{before['prices'][side]:.2f}→{after['prices'][side]:.2f}，去水权重上升{delta:.2f}个百分点")


def build(snapshot):
    row, base, signal, quote = (snapshot[k] for k in ('match', 'baseline', 'oddsSignal', 'quote'))
    change = signal['primary']
    if not signal['eligible'] or not change or not quote:
        raise ValueError('A verified change and a current Asian quote are required')
    hrate, arate = base['expectedGoals']
    grid = [([h, a], math.exp(-hrate-arate) * hrate**h * arate**a / math.factorial(h) / math.factorial(a))
            for h in range(13) for a in range(13)]
    if change['market'] in ('asian-handicap', '90-minute-1x2') and change['side'] in ('H', 'A'):
        side = change['side']
    else:
        # A totals/draw move does not establish a team direction. Use the recorded
        # form distribution and actual handicap price, and label that distinction.
        side = max('HA', key=lambda s: sum(w * profit(score, quote, s) for score, w in grid))
    total_quote = next((q for q in row.get('quotes', []) if q.get('market') == 'total-goals'
                        and q.get('phase') == 'latest' and q.get('provider') == quote.get('provider')
                        and q.get('via') == quote.get('via') and valid_quote(q, snapshot['at'], snapshot['cutoff'])
                        and snapshot['at'] - dt(q['fetchedAt']) <= timedelta(minutes=15)), None)
    # Select two scenarios compatible with the chosen handicap. This is a fixed
    # experimental ranking, not a fitted probability or an unconditional mode.
    def rank(item):
        score, weight = item
        distance = abs(score[0] - score[1] + quote['line'])
        total_distance = abs(sum(score) - total_quote['line']) if total_quote else 0
        return weight * math.exp(-.35 * distance - .15 * total_distance)
    compatible = sorted((item for item in grid if profit(item[0], quote, side) >= 0), key=rank, reverse=True)
    scores = [item[0] for item in compatible[:2]]
    own = row['teams']['home' if side == 'H' else 'away']['label']
    line = quote['line'] * (1 if side == 'H' else -1)
    line_text = '平手' if line == 0 else ('让' if line < 0 else '受让') + f'{abs(line):g}球'
    price = quote['prices'][side]
    chosen = '、'.join(':'.join(map(str, s)) for s in scores)
    previous = snapshot.get('initialPrediction')
    unchanged = previous and previous.get('asianSide') == side and previous.get('score') == scores[0]
    evidence = []
    for place in ('home', 'away'):
        team = snapshot['research']['teams'][place]
        name = row['teams'][place]['label']
        form = team.get('form', {})
        text = f"{name}：{form.get('summary') or str(base['samples'][place]) + '场往绩纳入统计'}。"
        for kind, label in [('previous', '上一场'), ('headToHead', '上次对赛')]:
            diff = team.get('comparisons', {}).get(kind, {}).get('difference', {})
            if diff.get('status') == 'available':
                incoming = '、'.join(p.get('mandarin') or p.get('name', '') for p in diff.get('in', []))
                text += f"与{label}首发相比保留{diff['retained']}人" + (f'，新上场{incoming}' if incoming else '') + '。'
        evidence.append(text)
    explanation = describe(change)
    reference_note = signal.get('referencePolicy', {}).get('note', '')
    detail = [
        {'title': '变盘记录', 'text': reference_note + explanation + '。H为主队，A为客队；比较同公司、同一市场。采集时间不等于变盘发生时间。'},
        {'title': '比分如何筛选', 'text': f"封存统计基线首选{base['leadingScores'][0][0]}:{base['leadingScores'][0][1]}。本版在所选亚洲盘不输盘的情境中，结合往绩泊松权重、净胜球距盘口中心和大小球线排序，取前两个比分。此筛选不代表其他比分不会发生，也未证明准确率提升。"},
        {'title': '阵容与往绩', 'text': ''.join(evidence)[:580]},
        {'title': '原因核查与限制', 'text': '报价变化是已核对事实；变化由伤停、轮换或资金造成，现有证据尚不能确认。正式首发和已收录天气、新闻可在本场资料展开核对；没有证据不据此调整权重。此版测试固定的顺变盘规则，赛后分别验证盘口方向、两个比分及反向对照。'},
    ]
    if previous:
        detail.append({'title': '与初版比较', 'text': ('方向和主比分沿用初版。' if unchanged else '本版依据最新可比报价及资料重新计算；初版独立保留。') + '首发确认仅代表名单已核实，不等于阵容强弱可以自动量化。'})
    summary = [f"主选{own}{line_text}，报价{price:.2f}；比分参考{chosen}（主队在前）。",
               explanation[:100] + '。按固定变盘规则试行，真实原因尚待证据验证。']
    return {'score': scores[0], 'scoreCandidates': scores, 'asianSide': side,
            'summary': summary, 'details': detail, 'model': VERSION}
