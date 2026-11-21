"""Read-only, fixture-bound observations for football post-match reviews."""
import json
import hashlib
import math
import re
from copy import deepcopy
from collections import defaultdict
from datetime import datetime

from .files import PUBLIC
from .leagues import league_path
from .evidence_reviews import new_dossier, add_source, add_fact

STAT_LABELS = dict(zip(
    'accurateCrosses accurateLongBalls accuratePasses blockedShots crossPct effectiveClearance effectiveTackles foulsCommitted interceptions longballPct offsides passPct penaltyKickGoals penaltyKickShots possessionPct redCards saves shotPct shotsOnTarget tacklePct totalClearance totalCrosses totalLongBalls totalPasses totalShots totalTackles wonCorners yellowCards'.split(),
    '成功传中 成功长传 成功传球 被封堵射门 传中成功率 有效解围 成功抢断 犯规 拦截 长传成功率 越位 传球成功率 点球进球 点球射门 控球率 红牌 扑救 射门转化率 射正 抢断成功率 解围 传中 长传 传球 射门 抢断 角球 黄牌'.split()))
STAT_LABELS['shots'] = '射门'
STAT_LABELS['shotPct'] = '射门比例（来源口径）'
MARKET_LABELS = {'90-minute-1x2': '全场胜平负', 'asian-handicap': '全场亚洲让球', 'total-goals': '全场大小球'}
PRICE_LABELS = {'H': '主队', 'D': '平局', 'A': '客队', 'O': '大球', 'U': '小球'}
PHASE_LABELS = {'opening': '来源标记开盘', 'closing': '来源标记封盘', 'latest': '最新采样', 'preclosing': '封盘前采样'}


def _load(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def _time(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed if parsed.tzinfo else None
    except ValueError:
        return None


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _identity(match, league):
    teams = match.get('teams', {})
    return {'league': league, 'id': str(match.get('id', '')), 'kickoff': match.get('kickoff'),
            'date': match.get('date') or str(match.get('kickoff', ''))[:10],
            **{side: match.get(side) or teams.get(side, {}).get('name') for side in ('home', 'away')},
            **{side + 'Goals': match.get(side + 'Goals', teams.get(side, {}).get('goals')) for side in ('home', 'away')},
            'scoreScope': match.get('scoreScope', '90分钟含补时')}


def _detail_valid(detail, ident):
    if not detail or detail.get('completed') is not True:
        return False
    required = {'league': ident['league'], 'matchId': ident['id'], 'date': ident['date'],
                'home': ident['home'], 'away': ident['away']}
    if any(not v or detail.get(k) != v for k, v in required.items()):
        return False
    if detail.get('kickoff') and _time(detail['kickoff']) != _time(ident['kickoff']):
        return False
    return not any(k in detail and detail[k] != ident[k] for k in ('homeGoals', 'awayGoals'))


def _clock(value):
    parts = re.findall(r'\d+', str(value))
    return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0) if parts else (999, 0)


def _match_facts(d, detail, ident):
    src = add_source(d, detail['source'], '已完场比赛阵容、事件与技术统计', detail.get('updatedAt'))
    if not detail.get('kickoff'):
        d['gaps'].append('详情仅独立核对赛事 ID、双方与比赛日期，未提供独立开球时间字段。')
    events = sorted(detail.get('events', []), key=lambda e: _clock(e.get('clock')))
    goal_types = {'goal', 'penalty---scored', 'own-goal'}
    goals = [e for e in events if e.get('type') in goal_types]
    def scoring_side(e):
        return e.get('scoringSide') if e.get('type') == 'own-goal' else e.get('side')
    count = {side: sum(scoring_side(e) == side for e in goals) for side in ('home', 'away')}
    reconciled = (all(scoring_side(e) in count and _clock(e.get('clock'))[0] != 999 for e in goals)
                  and all(count[s] == ident[s + 'Goals'] for s in count)
                  and '点球' not in ident['scoreScope'])
    if not reconciled:
        d['gaps'].append('进球事件无法与最终比分及比分口径完整对账；不生成逐球领先或逆转叙事。乌龙球须核实得分方。')
    score = {'home': 0, 'away': 0}
    for event in events:
        kind, side = event.get('type'), event.get('side')
        if kind in goal_types and not reconciled:
            continue
        if kind not in goal_types | {'yellow-card', 'red-card', 'yellow-red-card', 'substitution', 'penalty---missed'}:
            continue
        names = '、'.join(p.get('name', '') for p in event.get('players', []) if p.get('name'))
        text = f"{ident.get(side, '未明确球队')}：{event.get('label', kind)}；{names or '球员未明确'}"
        if kind in goal_types:
            score[scoring_side(event)] += 1
            text += f"；比分 {score['home']}–{score['away']}"
        if kind == 'substitution':
            text += '（事件名单不表示换入换出顺序）'
        fid = add_fact(d, text, [src], time=event.get('clock', ''), before_event=False)
        d['timeline'].append({'time': event.get('clock', ''), 'text': text, 'evidenceIds': [fid]})
    for row in detail.get('statistics', []):
        if row.get('side') in ('home', 'away'):
            values = '；'.join(f'{STAT_LABELS[k]} {v}' for k, v in row.get('values', {}).items() if k in STAT_LABELS)
            if values:
                add_fact(d, f"{ident[row['side']]}全场统计：{values}。全场总数不能证明某次换人产生因果效果。", [src], category='statistics', time='全场结束', before_event=False)
    for side, lineup in detail.get('lineups', {}).items():
        if side not in ('home', 'away') or lineup.get('name') != ident[side]:
            d['gaps'].append('阵容球队身份缺失或不一致，已排除。')
            continue
        players = lineup.get('players', [])
        starters = [p.get('name') for p in players if p.get('starter') and p.get('name')]
        if len(starters) == 11 and len(set(starters)) == 11 and lineup.get('confirmed'):
            add_fact(d, f"{ident[side]}确认首发：{'、'.join(starters)}；登记阵型 {lineup.get('formation') or '未提供'}。", [src], category='lineup', time='首发名单')
        else:
            d['gaps'].append(f'{ident[side]}未具备完整确认的 11 人首发。')
        by_id = {str(p.get('espnId')): p for p in players if p.get('espnId')}
        for p in players:
            if not p.get('name'):
                continue
            if p.get('entered'):
                replaced = by_id.get(str(p.get('replaces')), {})
                text = f"{ident[side]}：{p['name']}换入"
                if replaced.get('name') and replaced.get('left') == p['entered'] and not replaced.get('redCards'):
                    text += f"，{replaced['name']}换出"
                fid = add_fact(d, text, [src], time=p['entered'], before_event=False)
                d['timeline'].append({'time': p['entered'], 'text': text, 'evidenceIds': [fid]})
            if p.get('left'):
                reason = '红牌离场' if p.get('redCards') else '离场（换出原因未独立确认）'
                add_fact(d, f"{ident[side]}：{p['name']}{reason}", [src], time=p['left'], before_event=False)
    d['timeline'].sort(key=lambda e: _clock(e['time']))
    d['gaps'].append('首发、阵型和换人能支持战术解释，但教练真实意图需采访原文；未提供采访时不能写成事实。')


def _odds(d, match, ident, folder):
    kickoff = _time(ident['kickoff'])
    rows = []
    history = _load(folder / 'odds-history.json')
    if history.get('league') == ident['league']:
        rows.extend({**q, 'market': '90-minute-1x2', 'prices': {s: q.get(s) for s in 'HDA'},
                     'source': q.get('source') or '/'+str((folder / 'odds-history.json').relative_to(PUBLIC)).replace('\\', '/')}
                    for q in history.get('matches', {}).get(ident['id'], []))
    markets = _load(folder / 'market-odds.json')
    if markets.get('league') == ident['league']:
        rows.extend(markets.get('history', {}).get(ident['id'], []))
        rows.extend(markets.get('matches', {}).get(ident['id'], []))
    rows.extend(match.get('quotes', []))
    groups = defaultdict(list)
    excluded = 0
    for q in rows:
        stamp = q.get('observedAt') or q.get('at') or q.get('fetchedAt')
        at = _time(stamp)
        market = q.get('market')
        keys = {'90-minute-1x2': 'HDA', 'asian-handicap': 'HA', 'total-goals': 'OU'}.get(market)
        prices = q.get('prices', {})
        line = q.get('line')
        if (not keys or not q.get('provider') or not q.get('source') or not kickoff or not at or at >= kickoff
                or q.get('inPlay') or q.get('matchId', ident['id']) != ident['id']
                or q.get('scope', '90-minute') != '90-minute'
                or not isinstance(prices, dict) or set(prices) != set(keys)
                or not all(_number(prices.get(k)) and 1 < prices[k] <= 10000 for k in keys)
                or (market != '90-minute-1x2' and not (_number(line) and abs(line) <= 30 and line * 4 == round(line * 4)))):
            excluded += 1
            continue
        key = (q['provider'], market, q.get('via', ''), q.get('phase', '采集快照'))
        groups[key].append((at, stamp, q))
    for (provider, market, via, phase), quotes in sorted(groups.items()):
        quotes.sort(key=lambda v: v[0])
        prior = None
        accepted = []
        for _, stamp, q in quotes:
            signature = (stamp, q.get('line'), tuple(sorted(q['prices'].items())))
            if prior and signature == prior[0]:
                continue
            source = add_source(d, q['source'], f'{provider} / {via} / {MARKET_LABELS[market]}', stamp)
            prices = q['prices']
            margin = (sum(1 / v for v in prices.values()) - 1) * 100
            price_text = '，'.join(f'{PRICE_LABELS[k]} {v}' for k, v in prices.items())
            line_text = f"盘口 {q.get('line')}，" if market != '90-minute-1x2' else ''
            text = f"{provider} {MARKET_LABELS[market]}（{PHASE_LABELS.get(phase, phase)}）赛前采集 {stamp}：{line_text}十进制赔率 {price_text}；隐含概率合计超额 {margin:.2f} 个百分点（不是实际利润）。"
            if market == 'asian-handicap':
                text += '让球线以主队为基准，负数为主让、正数为主受让；水位为十进制价格减 1。'
            if prior:
                prev = prior[1]
                if prev.get('line') == q.get('line'):
                    text += '同公司同市场同盘口价格变化：' + '，'.join(f'{PRICE_LABELS[k]} {prev["prices"][k]}→{prices[k]}' for k in prices)
                else:
                    text += f"盘口线变动 {prev.get('line')}→{q.get('line')}；不同盘口价格不作同线升降水比较。"
            fid = add_fact(d, text, [source], category='market', time=stamp, before_event=True)
            accepted.append((stamp, q, source, fid))
            prior = (signature, q)
        # Compare each exact line separately; a different settlement line is not a price move.
        lines = defaultdict(list)
        for item in accepted:
            lines[item[1].get('line')].append(item)
        for line, samples in lines.items():
            if len(samples) < 2:
                continue
            first, last = samples[0], samples[-1]
            changes = '；'.join(
                f'{PRICE_LABELS[k]} {first[1]["prices"][k]:g}→{last[1]["prices"][k]:g}'
                f'（变化 {last[1]["prices"][k] - first[1]["prices"][k]:+.4f}，'
                f'{(last[1]["prices"][k] / first[1]["prices"][k] - 1) * 100:+.2f}%）'
                for k in first[1]['prices'])
            line_text = f'盘口 {line:g}；' if line is not None else ''
            text = (f'{provider} {MARKET_LABELS[market]}（{PHASE_LABELS.get(phase, phase)}）同线采样汇总：'
                    f'{line_text}{len(samples)} 条记录；首个 {first[0]}；末个 {last[0]}；{changes}。'
                    '以上是已留存采样的首末值，不是正式开盘或封盘，不能代表中间没有反复。')
            if market == 'total-goals':
                under = sum(q['prices']['U'] < q['prices']['O'] for _, q, _, _ in samples)
                over = sum(q['prices']['O'] < q['prices']['U'] for _, q, _, _ in samples)
                text += (f'按记录条数计，大球价格较低 {over} 条，小球价格较低 {under} 条，'
                         f'相同 {len(samples) - under - over} 条；采样不等距，条数不是持续时间或成交量。')
            add_fact(d, text, list(dict.fromkeys(s[2] for s in samples)),
                     category='market-summary', time=f'{first[0]} / {last[0]}', before_event=True)
    d['gaps'].append(f'赔率仅采用开球前、同场且身份及时间有效的采集；排除 {excluded} 条缺时、赛中、异场或类型不明记录。首次/末次记录不自动等于开盘/临场封盘。')
    d['gaps'].append('赔率变动不能单独证明资金流入或庄家意图；无成交额、限额及可靠消息时间线时，原因未证实。历史交锋盘口仅是另一场背景样本，不能拼作本场变化。')
    if not groups:
        d['gaps'].append('缺少可验证的赛前赔率采集序列，无法重建本场盘口与价格变化。')


def _curated(d, ident):
    for case in _load(PUBLIC / 'review-evidence' / 'football.json').get('cases', []):
        expected = case.get('identity', {})
        keys = ('league', 'id', 'kickoff', 'home', 'away', 'homeGoals', 'awayGoals')
        if any(expected.get(k) != ident.get(k) or expected.get(k) is None for k in keys):
            continue
        sources = {s['id']: add_source(d, s['url'], s['title'], s.get('updatedAt'))
                   for s in case.get('sources', []) if s.get('id') and s.get('url') and s.get('title')}
        for fact in case.get('facts', []):
            refs = fact.get('sourceIds', [])
            if not fact.get('text') or not refs or any(ref not in sources for ref in refs):
                continue
            fid = add_fact(d, fact['text'], [sources[r] for r in refs], category=fact.get('category', 'observation'),
                           time=fact.get('time', ''), before_event=fact.get('beforeEvent'))
            if fact.get('timeline'):
                d['timeline'].append({'time': fact.get('time', ''), 'text': fact['text'], 'evidenceIds': [fid]})
        d['gaps'].extend(case.get('gaps', []))


def _original_quote(d, original, snapshot, ident):
    report = original if isinstance(original, dict) else {}
    saved = snapshot if isinstance(snapshot, dict) else {}
    quote = report.get('quote') or saved.get('quote')
    if not isinstance(quote, dict):
        return
    d['originalQuote'] = deepcopy(quote)
    market, prices = quote.get('market'), quote.get('prices', {})
    keys = {'90-minute-1x2': 'HDA', 'asian-handicap': 'HA', 'total-goals': 'OU'}.get(market)
    line = quote.get('line')
    if (not keys or not isinstance(prices, dict) or set(prices) != set(keys)
            or not all(_number(prices[k]) and 1 < prices[k] <= 10000 for k in keys)
            or not quote.get('provider') or not quote.get('source')
            or quote.get('matchId', ident['id']) != ident['id']
            or (market != '90-minute-1x2' and not (_number(line) and abs(line) <= 30 and line * 4 == round(line * 4)))):
        d['gaps'].append('原预测报价已原样保留，但缺少有效市场、价格或来源，不能作为可比较行情。')
        return
    stamp = quote.get('fetchedAt')
    captured, kickoff, issued = _time(stamp), _time(ident['kickoff']), _time(report.get('issuedAt'))
    before = bool(captured and kickoff and captured < kickoff and not quote.get('inPlay')
                  and (not issued or captured <= issued < kickoff))
    src = add_source(d, quote['source'], f"原预测采用报价：{quote['provider']}", stamp)
    label = '，'.join(f'{PRICE_LABELS[k]} {v}' for k, v in prices.items())
    line_text = f'，盘口 {line}（主队基准）' if market == 'asian-handicap' else f'，总进球线 {line}' if market == 'total-goals' else ''
    text = f"原预测采用报价：{quote['provider']}，{MARKET_LABELS[market]}{line_text}，十进制赔率 {label}；采集时间 {stamp or '未记录'}。此为原预测实际采用值，不自动视为正式开盘或封盘。"
    if not before:
        text += '采集与开球/发文时间不能完整证明当时为赛前有效报价，不纳入赛前变化序列。'
    add_fact(d, text, [src], category='market', time=stamp or '', before_event=before)


def _snapshot_facts(d, original, snapshot, ident, detail):
    """Only structured source observations from the exact saved pregame input."""
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get('research'), dict):
        d['gaps'].append('未取得原预测对应的赛前研究快照，不能把当前资料倒写为当时已知输入。')
        return
    report = original if isinstance(original, dict) else {}
    research, row = snapshot['research'], snapshot.get('match', {})
    captured = _time(research.get('pregame', {}).get('capturedAt'))
    saved, issued, kickoff = _time(snapshot.get('capturedAt')), _time(report.get('issuedAt')), _time(ident['kickoff'])
    updated = _time(research.get('updatedAt'))
    digest = hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    expected_id = ident['id'].removeprefix('espn:')
    if _detail_valid(detail, ident) and detail.get('eventId'):
        expected_id = str(detail['eventId'])
    league = row.get('league') or {'700': 'epl', '710': 'ligue1', '720': 'bundesliga', '730': 'seriea', '740': 'laliga'}.get(str(row.get('competitionId')))
    teams = row.get('teams', {})
    same_sides = all(teams.get(s, {}).get('name') == ident[s] and teams.get(s, {}).get('id')
                     and str(research.get('teams', {}).get(s, {}).get('teamId')) == str(teams[s]['id']) for s in ('home', 'away'))
    if (report.get('snapshotHash') != digest or not all((captured, saved, issued, kickoff))
            or not captured <= saved <= issued < kickoff or updated and not captured <= updated <= saved
            or research.get('message') or str(row.get('id')) != expected_id or str(research.get('eventId')) != expected_id
            or _time(row.get('kickoff')) != kickoff or _time(research.get('kickoff')) != kickoff
            or league != ident['league'] or not same_sides or row.get('started') is not False or row.get('finished') is not False):
        d['gaps'].append('原研究快照未通过原文哈希、同场身份或采集≤发文<开球核验，不提升为赛前已知事实。')
        return
    stamp = research['pregame']['capturedAt']
    count_before = len(d['facts'])
    def source_url(value):
        return isinstance(value, str) and value.startswith(('https://', 'http://'))
    for side in ('home', 'away'):
        team = research['teams'][side]
        lineup = team.get('lineup', {})
        players = lineup.get('players', [])
        ids = [p.get('id') for p in players if isinstance(p, dict)]
        if (source_url(research.get('source')) and lineup.get('confirmed') is True and len(players) == len(set(ids)) == 11
                and all(ids) and all(isinstance(p.get('name'), str) and p['name'].strip() for p in players)):
            src = add_source(d, research['source'], '原预测留存的已确认首发', stamp)
            add_fact(d, f"原预测输入已收录 {ident[side]} 首发：{'、'.join(p['name'] for p in players)}；登记阵型 {lineup.get('formation') or '未提供'}。未首发不能直接推断伤停。",
                     [src], category='lineup', time=stamp, before_event=True)
        seen = set()
        for prior in team.get('form', {}).get('matches', [])[:10]:
            if not isinstance(prior, dict):
                continue
            at = _time(prior.get('date'))
            gf, ga = prior.get('goalsFor'), prior.get('goalsAgainst')
            key = (prior.get('date'), prior.get('opponentId') or prior.get('opponent'), prior.get('homeAway'))
            if (key in seen or not at or at >= captured or not source_url(prior.get('source'))
                    or not prior.get('opponent') or prior.get('homeAway') not in ('home', 'away')
                    or not all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 99 for v in (gf, ga))):
                continue
            seen.add(key)
            src = add_source(d, prior['source'], '原预测留存的已完场往绩', stamp)
            venue = '主场' if prior['homeAway'] == 'home' else '客场'
            add_fact(d, f"原预测输入中的历史样本：{prior['date']} {ident[side]} {venue}对 {prior['opponent']}，进 {gf} 球、失 {ga} 球；比分口径 {prior.get('scope') or '未提供'}。这是另一场比赛，不是本场过程。",
                     [src], category='observation', time=stamp, before_event=True)
    weather = research.get('weather', {})
    fetched, target = _time(weather.get('fetchedAt')), _time(weather.get('forecastFor'))
    if (weather.get('status') == 'available' and source_url(weather.get('source')) and fetched and target
            and fetched <= captured and abs((target - kickoff).total_seconds()) <= 10800):
        values = [f'{label} {weather[key]}{unit}' for key, label, unit in [
            ('temperature', '气温', '℃'), ('windSpeed', '风速', '米/秒'), ('humidity', '相对湿度', '%')]
                  if _number(weather.get(key))]
        if values:
            src = add_source(d, weather['source'], '原预测留存的赛前天气预报', weather['fetchedAt'])
            add_fact(d, f"原预测已取得针对 {weather['forecastFor']} 的天气预报：{'；'.join(values)}。城市参考点预报，不是球场实测，不能单独解释赛果。",
                     [src], category='observation', time=weather['fetchedAt'], before_event=True)
    if len(d['facts']) == count_before:
        d['gaps'].append('快照身份与时间有效，但没有完整首发、带来源往绩或有效天气数值；模型摘要、解释、旧复盘建议不作已核实事实。')
    d['gaps'].append('赛前快照只证明资料已进入原预测输入，不证明模型遗漏或权重错误；须逐条对照原判断。')


def build_dossier(match, original, detail=None, league='epl', snapshot=None):
    """No refresh or network access; preserve the caller's original prediction."""
    if hasattr(match, 'model_dump'):
        match = match.model_dump()
    folder = PUBLIC if league == 'ligue1' else league_path(PUBLIC, league)
    ident = _identity(match, league)
    d = new_dossier('football', f"{league}:{ident['id']}", original)
    d['fixture'] = ident
    d['snapshot'] = snapshot
    d['overview'].append(f"{ident['home']} vs {ident['away']}；开球 {ident['kickoff'] or '未记录'}；比分口径 {ident['scoreScope']}")
    completed = match.get('finished') is True or match.get('completed') is True
    scores = all(isinstance(ident[s + 'Goals'], int) and not isinstance(ident[s + 'Goals'], bool) and ident[s + 'Goals'] >= 0 for s in ('home', 'away'))
    if completed and scores:
        filename = 'daily-football.json' if league == 'ligue1' or match.get('teams') else 'data.json'
        url = match.get('source') or '/'+str((folder / filename).relative_to(PUBLIC)).replace('\\', '/')
        src = add_source(d, url, '比赛最终结果', match.get('updatedAt'))
        add_fact(d, f"{ident['home']} {ident['homeGoals']}–{ident['awayGoals']} {ident['away']}（{ident['scoreScope']}）", [src], category='result', time=ident['date'])
        if _detail_valid(detail, ident) and detail.get('source'):
            _match_facts(d, detail, ident)
        else:
            d['gaps'].append('没有通过同场身份、日期与完场状态核验的比赛详情，不据此推断阵容、事件或战术。')
        _curated(d, ident)
    else:
        d['gaps'].append('比赛未确认完场或最终比分缺失，不进行赛后事件与战术归因。')
    _original_quote(d, original, snapshot, ident)
    _snapshot_facts(d, original, snapshot, ident, detail)
    _odds(d, match, ident, folder)
    d['gaps'].append('逐项检验原假设须引用原文与事实；未纳入但赛前已知的信息属于方法遗漏候选，比赛中发生不等于赛前不可预见。证据不足时保留未确定。')
    return d
