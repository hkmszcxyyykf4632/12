"""Auditable intent hypotheses, frozen before kickoff, with separate outcome checks."""
import hashlib
import json
from datetime import datetime, timedelta, timezone

from .files import publish, read_json

VERSION = 'intent-rules-1'


def dt(value):
    try:
        value = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return value if value.tzinfo else None
    except (TypeError, ValueError):
        return None


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def table_evidence(row, side, context, at):
    table = context.get('table', {})
    stamp = dt(table.get('updatedAt'))
    season = str(table.get('season', '')).split('/')[0]
    if not stamp or not timedelta(0) <= at - stamp <= timedelta(hours=48) or season != str(row.get('season')):
        return None
    entries = table.get('entries', [])
    own = next((r for r in entries if str(r.get('espnId')) == row['teams'][side]['id']), None)
    other = next((r for r in entries if str(r.get('espnId')) == row['teams']['away' if side == 'home' else 'home']['id']), None)
    if not own or not other or not all(isinstance(r.get(k), int) for r in (own, other) for k in ('rank', 'points', 'played')):
        return None
    if min(own['played'], other['played']) < 3:
        return None
    return {'own': own, 'opponent': other, 'count': len(entries), 'source': table.get('source'), 'asOf': table['updatedAt']}


def team_hypothesis(row, side, context, at):
    own, rival = row['teams'][side], row['teams']['away' if side == 'home' else 'home']
    home = side == 'home' and not row.get('neutral')
    evidence = [{'title': '比赛场地', 'fact': '中立场' if row.get('neutral') else '主场' if home else '客场',
                 'inference': '场地只用于战术倾向判断，不能单独确认战意。',
                 'source': row['source'], 'asOf': row['updatedAt']}]
    form, opposing = own.get('form', ''), rival.get('form', '')
    if form:
        evidence.append({'title': '来源所列近期战绩', 'fact': f'{len(form)}场：{form.count("W")}胜、{form.count("D")}平、{form.count("L")}负',
                         'inference': '近期成绩用于判断取分压力；连败不代表主动求败。',
                         'source': row['source'], 'asOf': row['updatedAt']})
    table = table_evidence(row, side, context, at)
    tendency, why, confidence = '待确认', '当前可核实资料不足以区分争胜或保平部署。', '资料不足'
    if table:
        t, opponent = table['own'], table['opponent']
        evidence.append({'title': '赛前积分形势',
                         'fact': f'本队第{t["rank"]}、{t["points"]}分（{t["played"]}场）；对手第{opponent["rank"]}、{opponent["points"]}分（{opponent["played"]}场）',
                         'inference': '排名与分差用于识别取分压力，不宣称已经锁定晋级、保级或必须赢球。',
                         'source': table['source'], 'asOf': table['asOf']})
        confidence = '中低'
        if t['rank'] >= table['count'] - 2 or t['rank'] <= 4:
            tendency, why = '争胜优先', '积分位置带来较强取分需求，争取三分的倾向较高。'
        elif not home and t['rank'] - opponent['rank'] >= 6 and opponent['points'] - t['points'] >= 6:
            tendency, why = '保平倾向', '客场面对积分明显更高的对手，稳守取分、接受平局的可能性较高。'
        else:
            tendency, why = '争胜优先', '没有足够资料支持保平足够的判断，按常规争取三分处理。'
    elif len(form) >= 3 and len(opposing) >= 3:
        confidence = '低'
        if not home and form.count('L') >= 3 and opposing.count('W') >= 3:
            tendency, why = '保平倾向', '近期表现处于下风且作客，推测会更重视避免失利。'
        elif home and form.count('W') >= 3:
            tendency, why = '争胜优先', '主场与近期胜绩支持主动争胜的初步判断。'
    fixtures = context.get('live', {}).get('matches', [])
    next_dates = [dt(m.get('kickoff')) for m in fixtures
                  if own['name'] in (m.get('home'), m.get('away')) and dt(m.get('kickoff'))
                  and dt(m['kickoff']) > dt(row['kickoff']) + timedelta(hours=6)]
    if next_dates:
        hours = (min(next_dates) - dt(row['kickoff'])).total_seconds() / 3600
        if hours <= 96:
            evidence.append({'title': '已收录后续赛程', 'fact': f'约{hours / 24:.1f}天后另有一场比赛',
                             'inference': '密集赛程可能影响轮换；尚未由本场首发确认。',
                             'source': context.get('live', {}).get('source') or row['source'],
                             'asOf': context.get('live', {}).get('updatedAt')})
            confidence = '低' if tendency != '待确认' else confidence
    draw = '较高' if tendency == '保平倾向' else '较低' if tendency == '争胜优先' else '待确认'
    checks = [] if tendency == '待确认' else [
        {'id': 'result', 'label': '全场取胜' if tendency == '争胜优先' else '全场不败',
         'rule': 'win' if tendency == '争胜优先' else 'unbeaten'},
        {'id': 'shots', 'label': '射门占比至少55%' if tendency == '争胜优先' else '射门占比不高于45%',
         'rule': 'shots_ge_55' if tendency == '争胜优先' else 'shots_le_45'}]
    return {'teamId': own['id'], 'team': own['label'], 'tendency': tendency, 'drawAcceptance': draw,
            'loseIntent': '无法判断', 'confidence': confidence, 'summary': why,
            'evidence': evidence, 'missing': ['已核实的本场教练赛前言论', '确认首发与轮换', '完整伤停与杯赛晋级条件'],
            'checks': checks}


def build_original(row, context, at):
    if row['state'] != 'scheduled' or row.get('started') or not dt(row['kickoff']) or at >= dt(row['kickoff']):
        return None
    result = {'version': VERSION, 'eventId': row['id'], 'generatedAt': at.isoformat(), 'kickoff': row['kickoff'],
              'method': '公开数据规则分析；标签是战术与取分意图假设，非球队公开承诺或胜率。',
              'reviewMethod': '赛后分别核对赛前登记的结果和射门指标；指标符合不等于证实主观心态。',
              'teams': {side: team_hypothesis(row, side, context, at) for side in ('home', 'away')}}
    return {**result, 'hash': digest(result)}


def verify_original(original, row):
    if not original or original.get('hash') != digest({k: v for k, v in original.items() if k != 'hash'}):
        return False
    issued, kickoff = dt(original.get('generatedAt')), dt(row.get('kickoff'))
    return bool(issued and kickoff and issued < kickoff and original.get('eventId') == row['id'] and
                all(original.get('teams', {}).get(side, {}).get('teamId') == row['teams'][side]['id'] for side in ('home', 'away')))


def review_match(row, original):
    if not verify_original(original, row):
        return {'status': '无有效赛前记录', 'summary': '这场比赛未留存有效的赛前战意分析，不补写赛前结论。', 'teams': {}}
    if not row['finished']:
        return {'status': '待赛后验证', 'summary': '赛前结论已留存，完场并取得赛果后自动核对。', 'teams': {}}
    teams = {}
    for side, hypothesis in original['teams'].items():
        own, rival = row['teams'][side], row['teams']['away' if side == 'home' else 'home']
        scored, conceded = own['goals'], rival['goals']
        normal = row.get('scoreScope') == '90分钟含补时' and all(isinstance(x, int) for x in (scored, conceded))
        a, b = own.get('shots'), rival.get('shots')
        share = a / (a + b) if all(isinstance(x, (int, float)) and x >= 0 for x in (a, b)) and a + b >= 6 else None
        checks = []
        for check in hypothesis['checks']:
            rule = check['rule']
            passed = ((scored > conceded if rule == 'win' else scored >= conceded) if normal else None) if check['id'] == 'result' else (
                (share >= .55 if rule == 'shots_ge_55' else share <= .45) if share is not None and normal else None)
            observed = (f'{scored} : {conceded}' if normal else '缺少可核实的90分钟赛果') if check['id'] == 'result' else (
                f'{a:g} : {b:g}次，{share:.0%}' if share is not None and normal else '射门资料不足或包含加时')
            checks.append({**check, 'observed': observed, 'passed': passed})
        checked = [c for c in checks if c['passed'] is not None]
        teams[side] = {'checks': checks, 'supported': sum(c['passed'] for c in checked), 'checked': len(checked),
                       'summary': f'{sum(c["passed"] for c in checked)}/{len(checked)}项赛前指标得到支持' if checked else '现有资料不足以验证赛前倾向'}
    return {'status': '已复核', 'checkedAt': row['updatedAt'], 'source': row['source'], 'teams': teams,
            'summary': '比赛结果和表现指标已与原记录对照；它们不能直接证明球队内心的输赢意图。'}


def attach_research(row, rows, contexts, at, folder):
    path = folder / (row['id'] + '.json')
    try:
        original = read_json(path)
    except (OSError, ValueError):
        original = None
    fresh = dt(row.get('updatedAt')) and timedelta(0) <= at - dt(row['updatedAt']) <= timedelta(minutes=3)
    if original is None and not path.exists() and fresh:
        original = build_original(row, contexts.get(row.get('league'), {}), at)
        if original:
            publish(path, original)
    row['motivation'] = {'original': original if verify_original(original, row) else None,
                         'review': review_match(row, original)}
