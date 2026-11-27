"""Deterministic audits over verified dossiers; never calls a generation service."""
import math
import re


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def score(value):
    return isinstance(value, (list, tuple)) and len(value) == 2 and all(type(v) is int and 0 <= v <= 30 for v in value)


def display(value):
    return ':'.join(map(str, value))


def refs(items):
    return list(dict.fromkeys(e for item in items for e in item.get('evidenceIds', [item.get('id')]) if e))[:30]


def join_facts(items, limit=1100):
    parts, size = [], 0
    for item in items:
        text = (str(item.get('time') or item.get('clock') or '') + ' ' + item['text']).strip()
        if size + len(text) > limit:
            break
        parts.append(text.rstrip('。；'))
        size += len(text) + 1
    return '；'.join(parts)


def driver(result, title, explanation, evidence, kind='observed'):
    if evidence and len(result['drivers']) < 12:
        result['drivers'].append({'title': title, 'kind': kind, 'explanation': explanation[:1400], 'evidenceIds': refs(evidence)})


def lesson(result, title, explanation, check, evidence, claim_ids=(), category='unresolved'):
    if evidence and len(result['lessons']) < 10:
        result['lessons'].append({'title': title, 'category': category, 'explanation': explanation[:1400],
                                 'nextCheck': check, 'evidenceIds': refs(evidence), 'claimIds': list(claim_ids)})


def football_outcome(d):
    original, fixture = d.get('original') or {}, d.get('fixture') or {}
    actual = [fixture.get('homeGoals'), fixture.get('awayGoals')]
    if not score(actual) or str(fixture.get('scoreScope', '')).replace(' ', '') != '90分钟含补时':
        return None
    result_facts = [f for f in d['facts'] if f['category'] == 'result']
    if not result_facts:
        return None
    targets = original.get('scoreCandidates') or [original.get('score')]
    targets = [list(v) for v in targets if score(v)]
    outcome = {'actual': actual, 'targets': targets, 'exact': actual in targets if targets else None,
               'evidence': result_facts, 'asian': None, 'quoteEvidence': []}
    q = d.get('originalQuote') or {}
    line = q.get('line')
    quote_facts = [f for f in d['facts'] if f['category'] == 'market' and f['text'].startswith('原预测采用报价：') and f.get('beforeEvent') is True]
    if quote_facts and number(line) and abs(line) <= 30 and line * 4 == round(line * 4) and original.get('asianSide') in ('H', 'A'):
        from .football_forecasts import settlement
        outcome['asian'] = settlement(actual, line, original['asianSide'])
        outcome['quoteEvidence'] = quote_facts
        outcome['line'] = line
    return outcome


def audit_targets(d, result, outcome):
    facts = d['facts']
    original = d.get('original') or {}
    for claim in d['claims']:
        kind, value = claim.get('kind'), claim.get('value')
        verdict, evidence = 'unresolved', []
        text = '这段包含理由或条件判断，不能仅凭赛果判定整段成立或错误。'
        if kind == 'score' and outcome and outcome['targets']:
            verdict = 'supported' if outcome['exact'] else 'contradicted'
            text = f"保存的比分选择 {'、'.join(map(display, outcome['targets']))}，实际 {display(outcome['actual'])}；比分{'命中' if outcome['exact'] else '未命中'}。比分目标与亚洲盘单独结算。"
            evidence = outcome['evidence']
        elif kind == 'asianSide' and outcome:
            status = outcome['asian']
            if status:
                verdict = 'supported' if status in ('赢盘', '赢半') else 'contradicted' if status in ('输盘', '输半') else 'unresolved'
                text = f"按原预测采用的主队基准盘口 {outcome['line']:+g}、{value}方向结算：{status}。赢半和输半保留半注结果；走盘不计命中。"
                evidence = outcome['evidence'] + outcome['quoteEvidence']
            else:
                text = '未选边，或缺少可核对的赛前采用盘口；不以赛后盘口代替原值结算。'
        elif kind == 'pick':
            picked = next((e for e in d.get('raceContext', {}).get('entries', []) if e['id'] == value), None)
            if picked and not picked.get('withdrawn') and type(picked.get('place')) is int:
                verdict = 'supported' if picked['place'] == 1 else 'contradicted'
                text = f"原独赢首选 {picked['number']}号{picked['name']}，正式名次 {picked['place']}；独赢{'命中' if picked['place'] == 1 else '未命中'}。位置、连赢及回报须分别按所选组合和官方派彩核算。"
                evidence = [picked]
            else:
                text = '首选退出或正式名次未核实，不计成失败，也不补选替代马匹。'
        elif kind in ('week', 'quarter'):
            h = d.get('priceContext', {}).get('horizons', {}).get(kind, {})
            evidence = [f for f in facts if f['category'] == 'outcome' and f['text'].startswith('短期' if kind == 'week' else '中期')]
            if h.get('correct') is not None:
                verdict = 'supported' if h['correct'] else 'contradicted'
            text = join_facts(evidence) or '该预测周期尚无足够的已确认收盘记录。'
        elif outcome and re.search('比分|主选|亚盘|亚洲盘', claim['text']):
            text += f"已核实实际比分 {display(outcome['actual'])}。"
            if outcome['targets']:
                text += '原比分选择' + ('命中。' if outcome['exact'] else '未命中。')
            if outcome['asian']:
                text += f"原亚洲盘{outcome['asian']}。"
            text += '具体目标已在独立条目核对；原文中的阵容、走势原因仍须各自取证。'
            evidence = outcome['evidence'] + outcome['quoteEvidence']
        else:
            categories = ('lineup',) if re.search('阵容|首发|换人|轮换', claim['text']) else ('market-summary',) if re.search('赔率|盘口|开盘|水位', claim['text']) else ('sectionals', 'running') if d['domain'] == 'racing' else ('observation', 'statistics')
            evidence = [f for f in facts if f['category'] in categories][:2]
            if evidence:
                text += '可对照的记录：' + join_facts(evidence, 850)
            text += '只有核对当时输入、过程及其他解释后，才判定是否属于方法遗漏。'
        result['claimAudits'].append({'claimId': claim['id'], 'verdict': verdict, 'explanation': text[:1400], 'evidenceIds': refs(evidence)})


def football_process(d, result, outcome):
    context = d.get('matchContext') or {}
    events = context.get('events', [])
    goals = [e for e in events if e['type'] in ('goal', 'penalty---scored', 'own-goal')]
    if goals and context.get('goalsReconciled'):
        driver(result, '进球顺序与比分转折', join_facts(goals) + '。以上进球已与最终比分对账；事件中的球员名单不自动区分进球者和助攻者。', goals)
    if outcome and outcome['targets'] and goals and context.get('goalsReconciled'):
        exceeded = next((e for e in goals if all(any(e['after'][i] > target[i] for i in (0, 1)) for target in outcome['targets'])), None)
        if exceeded:
            driver(result, '比分选择何时被突破',
                   f"{exceeded['clock']} 比分来到 {display(exceeded['after'])}，已使保存的比分选择 {'、'.join(map(display, outcome['targets']))}全部无法成为最终比分。"
                   '这一时点定位了比分预测落空的阶段。之后的红牌、换人或进球不能反过来解释此前已经形成的偏差，仍应追查此前失球与机会产出的原因。', [exceeded])
    critical = [e for e in events if e['type'] in ('red-card', 'yellow-red-card', 'penalty---missed', 'penalty---scored', 'own-goal')]
    if critical:
        parts = []
        for e in critical[:6]:
            before = f"事件前比分 {display(e['before'])}；" if score(e.get('before')) else '事件前比分未完整核实；'
            parts.append(f"{e['clock']} {before}{e['text']}")
        driver(result, '红牌、点球与特殊事件的时点', '；'.join(parts) + '。事件发生前已经形成的比分不能归因于该事件。这里只确认先后顺序；若要估计影响大小，还需分时段机会质量与人数变化。', critical)
        lesson(result, '特殊事件与预测误差分开核对', '已记录上述赛中事件，但单场事实不能证明无此事件时必然出现另一结果，也不能把全部偏差归咎于意外。',
               '保留事件前后比分、射门与在场人数；将有红牌/点球和无此类事件的样本分组比较，检查盘口与比分误差。', critical, category='unexpected')
    for side in ('home', 'away'):
        subs = [e for e in events if e['type'] == 'substitution' and e['side'] == side]
        if not subs:
            continue
        parts = []
        for e in subs[:7]:
            state = f"当时 {display(e['before'])}，" if score(e.get('before')) else ''
            parts.append(f"{e['clock']} {state}{e['text']}")
        name = d.get('fixture', {}).get(side) or ('主队' if side == 'home' else '客队')
        driver(result, name + '的换人时机', '；'.join(parts) + '。可确认教练何时调整人员；攻守意图及调整效果需结合球员位置、换人前后分段表现和采访，不能把随后进球直接算作换人功劳。', subs)
    stats = [f for f in d['facts'] if f['category'] == 'statistics']
    if stats:
        readings = []
        for fact in stats[:2]:
            values = re.findall(r'(?:：|；)(控球率|射门|射正|角球|红牌)\s+([0-9.]+)', fact['text'])
            team = fact['text'].split('全场统计：', 1)[0]
            readings.append(team + '：' + '，'.join(label + ' ' + value for label, value in values) if values else fact['text'][:220])
        driver(result, '机会产出与全场表现', '；'.join(readings) + '。射门和射正反映机会数量，尚不能替代预期进球或机会质量；全场合计也不能分辨领先后收缩与始终被动。完整统计可展开证据查看。', stats[:2])
    if outcome and outcome['targets'] and not outcome['exact']:
        primary = outcome['targets'][0]
        actual = outcome['actual']
        ref = goals + stats + outcome['quoteEvidence']
        if ref:
            explanation = (f"主比分 {display(primary)}，实际 {display(actual)}；总入球偏差 {sum(actual)-sum(primary):+d}，主队净胜球偏差 {(actual[0]-actual[1])-(primary[0]-primary[1]):+d}。"
                           '这定位了比分选择偏差，但尚不足以区分进球率估计、比分筛选条件与单场波动。')
            lesson(result, '比分究竟错在方向还是幅度', explanation,
                   '按联赛、主客场、开赛前盘口和变盘幅度分组，分别统计净胜球误差、总进球误差及两个比分覆盖率；与冻结的原基线对照，再决定是否改参数。',
                   ref, [c['id'] for c in d['claims'] if c.get('kind') == 'score'])
    lineups = [f for f in d['facts'] if f['category'] == 'lineup']
    if lineups:
        driver(result, '阵容核对的证据边界', join_facts(lineups[:2]) + '。赛后保存的首发只证明本场名单；只有带赛前时间戳的封存输入才能证明发布预测时已经掌握该名单。', lineups[:2])


def market_process(d, result, outcome):
    summaries = [f for f in d['facts'] if f['category'] == 'market-summary']
    if outcome and outcome['quoteEvidence']:
        quote = outcome['quoteEvidence'][0]
        result['marketReview'].append({'title': '原采用盘口与实际输赢',
            'explanation': quote['text'] + f" 完场 {display(outcome['actual'])}，原方向{outcome['asian']}。净胜球加原主队盘口为 {outcome['actual'][0]-outcome['actual'][1]+outcome['line']:+g}；四分之一盘按两条半注盘口分别结算。该场结算只是单个样本，不能证明变盘具有长期预测能力。",
            'evidenceIds': refs([quote] + outcome['evidence'])})
    for f in summaries[:6]:
        result['marketReview'].append({'title': '同口径报价变化', 'explanation': f['text'] + '。报价的变化与赛果同时记录，不能直接推断资金方向、内幕消息或变化造成赛果。需与同联赛同盘口的未变盘、顺向及反向样本比较。', 'evidenceIds': [f['id']]})
    if not summaries:
        odds = [f for f in d['facts'] if f['category'] in ('odds', 'market')]
        if odds:
            selected = odds[-3:]
            result['marketReview'].append({'title': '当前可核对的报价记录', 'explanation': join_facts(selected, 1000) + '。这些记录尚未构成完整、同口径的开盘至封盘路径，不评价趋势的预测效力。', 'evidenceIds': refs(selected)})


def racing_process(d, result):
    original = d.get('original') or {}
    picked = next((e for e in d.get('raceContext', {}).get('entries', []) if e['id'] == original.get('pick')), None)
    if picked:
        result['summary'].append(f"原首选 {picked.get('number')}号{picked['name']}；正式名次 {picked.get('place') or '未核实'}。独赢与位置、组合投注分别评估，不以每场中一匹代替每注命中率。")
    running = [f for f in d['facts'] if f['category'] == 'running']
    splits = [f for f in d['facts'] if f['category'] == 'sectionals']
    preferred = [f for f in running + splits if picked and picked['name'] in f['text']]
    if preferred:
        driver(result, '首选马实际跑法与分段', join_facts(preferred), preferred)
    if running:
        driver(result, '沿途走位与最终名次', join_facts(running[:6]) + '。走位变化只说明名次推进或后退；没有每段距离及时间，不能据此认定步速过快或留后有利。', running[:6])
    if splits:
        driver(result, '本场实录分段', join_facts(splits[:5]) + '。比较只限这场已核对的途程和分段，跨距离分段秒数不直接比较。', splits[:5])
    evidence = preferred or splits[:2] or running[:2]
    if evidence:
        lesson(result, '核对预期跑法是否实现', '实际走位与分段已经留档；受阻、伤患和骑师决策仍需竞赛董事报告或录像支持。没有当时保存的预期步速，不能事后声称已经考虑过。',
               '逐匹对照赛前预计位置、出闸后位置、最后两段与头马距离；按班次、场地和步速分组验证，再讨论训练或跑法权重。', evidence)
    equipment = [f for f in d['facts'] if f['category'] == 'equipment']
    if equipment:
        driver(result, '装备记录', join_facts(equipment[:4]), equipment[:4])


def stock_process(d, result):
    context = d.get('priceContext') or {}
    path = context.get('path') or []
    facts = d['facts']
    if context.get('periodReturn') is not None:
        result['summary'].append(f"自基准 {context['baselineDate']} 至 {context['asOf']}，复权收盘收益 {context['periodReturn']:+.2%}，收盘路径最大回撤 {context['maxDrawdown']:.2%}。短期和中期分别按原定交易日到期检验。")
    dated = {f.get('time'): f for f in facts if f['category'] == 'observation' and '复权收盘' in f['text']}
    movers = sorted((r for r in path if number(r.get('dailyReturn'))), key=lambda r: abs(r['dailyReturn']), reverse=True)[:3]
    evidence = [dated[r['date']] for r in movers if r['date'] in dated]
    if evidence:
        driver(result, '区间内最大收盘波动', join_facts(evidence) + '。这些是同口径价格路径，未有同日公告、行业或指数的对照证据，不能归因于某条新闻。', evidence)
    volume = sorted((r for r in path if number(r.get('volumeRatioToPrior20'))), key=lambda r: r['volumeRatioToPrior20'], reverse=True)[:2]
    volumes = [dated[r['date']] for r in volume if r['date'] in dated]
    if volumes:
        driver(result, '量能放大与价格同日对照', join_facts(volumes) + '。均量使用此前20条日线，不含当日。成交量增加本身不能区分买卖动机，也不能证明次日延续。', volumes)
    if evidence:
        lesson(result, '区分预测周期与短时波动', '区间路径用于观察风险，只有原定周期到期才评估方向；尚缺可比市场基准，无法区分个股判断与大盘共同变动。',
               '补齐同币种同复权基准、停牌和公司公告首次公开时间，再分别评估方向、最大回撤与超额收益；保留原发布时点。', evidence)


def generate(dossier):
    result = {'summary': [], 'claimAudits': [], 'drivers': [], 'lessons': [], 'marketReview': []}
    domain = dossier['domain']
    outcome = football_outcome(dossier) if domain == 'football' else None
    if outcome:
        text = f"90分钟赛果 {display(outcome['actual'])}。"
        if outcome['targets']:
            text += '保存的比分选择 ' + '、'.join(map(display, outcome['targets'])) + ('命中。' if outcome['exact'] else '未命中。')
        if outcome['asian']:
            text += f"原亚洲盘{outcome['asian']}。"
        text += '比分、亚洲盘与判断依据分别核对。'
        result['summary'].append(text)
    if domain == 'football':
        football_process(dossier, result, outcome)
    elif domain == 'racing':
        racing_process(dossier, result)
    elif domain == 'stocks':
        stock_process(dossier, result)
    audit_targets(dossier, result, outcome)
    market_process(dossier, result, outcome)
    # Attributed supplements still appear even if no specialized context exists.
    if not result['drivers']:
        supplemental = [f for f in dossier['facts'] if f['category'] not in ('result', 'market', 'odds', 'method', 'outcome')][:5]
        if supplemental:
            driver(result, '可核对的过程记录', join_facts(supplemental), supplemental, kind='inference')
    if not result['summary']:
        result['summary'] = [str(p)[:240] for p in dossier.get('overview', [])[:1]] or ['已按保存的预测与来源记录完成事实对照。']
    if dossier.get('gaps'):
        result['summary'].append('仍待核实：' + '；'.join(dossier['gaps'][:2])[:180])
    result['summary'].append('本次由站内规则自动核对。过程记录与推断分开；缺少原因证据的判断保持未定，后续资料到齐会另存新复盘。')
    result['summary'] = result['summary'][:3]
    return result
