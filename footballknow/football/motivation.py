"""Frozen match context and conditional scenarios, separate from team intent and forecasts."""
import hashlib
import json
from datetime import datetime, timedelta, timezone

from .files import publish, read_json

VERSION = 'match-context-2'


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
    own = row['teams'][side]
    home = side == 'home' and not row.get('neutral')
    evidence = [{'title': '比赛场地', 'fact': '中立场' if row.get('neutral') else '主场' if home else '客场',
                 'inference': '场地是比赛条件，不能据此判断球队争胜或接受平局。',
                 'source': row['source'], 'asOf': row['updatedAt']}]
    form = ''.join(c for c in str(own.get('form') or '').upper() if c in 'WDL')
    if form:
        evidence.append({'title': '来源所列近期战绩', 'fact': f'{len(form)}场：{form.count("W")}胜、{form.count("D")}平、{form.count("L")}负',
                         'inference': '这是已发生的成绩，不代表本场比赛目标或战术部署。',
                         'source': row['source'], 'asOf': row['updatedAt']})
    table = table_evidence(row, side, context, at)
    if table:
        t, opponent = table['own'], table['opponent']
        evidence.append({'title': '赛前积分形势',
                         'fact': f'本队第{t["rank"]}、{t["points"]}分（{t["played"]}场）；对手第{opponent["rank"]}、{opponent["points"]}分（{opponent["played"]}场）',
                         'inference': '排名与积分提供取分背景，不能确认球队必须赢球或平局足够。',
                         'source': table['source'], 'asOf': table['asOf']})
        evidence.append({'title': '本场取分影响',
                         'fact': f'按联赛胜3分、平1分计算：本队取胜后为{t["points"] + 3}分，打平后为{t["points"] + 1}分；最终排名还取决于其他赛果。',
                         'inference': '这是积分算术，不是球队已表态的目标，也不是胜率或比分预测。',
                         'source': table['source'], 'asOf': table['asOf']})
    fixtures = context.get('live', {}).get('matches', [])
    next_dates = [dt(m.get('kickoff')) for m in fixtures
                  if own['name'] in (m.get('home'), m.get('away')) and dt(m.get('kickoff'))
                  and dt(m['kickoff']) > dt(row['kickoff']) + timedelta(hours=6)]
    if next_dates:
        hours = (min(next_dates) - dt(row['kickoff'])).total_seconds() / 3600
        if hours <= 96:
            evidence.append({'title': '已收录后续赛程', 'fact': f'约{hours / 24:.1f}天后另有一场比赛',
                             'inference': '若进行轮换，需由首发或教练说明确认；密集赛程不等于放弃本场。',
                             'source': context.get('live', {}).get('source') or row['source'],
                             'asOf': context.get('live', {}).get('updatedAt')})
    return {'teamId': own['id'], 'team': own['label'],
            'summary': '；'.join(e['fact'] for e in evidence if e['title'] != '本场取分影响'),
            'goalStatus': '现有资料未收录可核对的本场目标表态；不从排名或近况推断争胜、保平心态。',
            'scenarios': ['若比分落后且需要追分，可观察是否增加前场投入；这是假设情境，不是已确认部署。',
                          '若比分领先，可观察是否减少冒险、加强防守；不能据此反推赛前只想保平。'],
            'evidence': evidence, 'missing': ['已核实的本场教练赛前言论', '确认首发与轮换', '完整伤停与杯赛晋级条件'],
            'checks': []}


def build_original(row, context, at):
    if row['state'] != 'scheduled' or row.get('started') or not dt(row['kickoff']) or at >= dt(row['kickoff']):
        return None
    result = {'version': VERSION, 'eventId': row['id'], 'generatedAt': at.isoformat(), 'kickoff': row['kickoff'],
              'method': '公开资料整理：积分与近况是客观背景；比赛目标须有本场明确表态，战术情境是条件假设，比分预测独立呈现。',
              'reviewMethod': '赛后仅记录比分与射门等表现，不以赛果或射门占比检验球队内心意图。',
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
        return {'status': '无有效赛前记录', 'summary': '这场比赛未留存有效赛前记录，不补写当时的目标或部署。', 'teams': {}}
    if not row['finished']:
        return {'status': '待赛后记录', 'summary': '赛前客观资料已留存，完场后仅记录结果与表现。', 'teams': {}}
    teams = {}
    for side in original['teams']:
        own, rival = row['teams'][side], row['teams']['away' if side == 'home' else 'home']
        scored, conceded = own['goals'], rival['goals']
        normal = row.get('scoreScope') == '90分钟含补时' and all(isinstance(x, int) for x in (scored, conceded))
        a, b = own.get('shots'), rival.get('shots')
        valid_shots = normal and all(isinstance(x, (int, float)) and x >= 0 for x in (a, b))
        observations = [{'label': '90分钟比分（本队在前）', 'observed': f'{scored} : {conceded}' if normal else '缺少可核实的90分钟赛果'}]
        if valid_shots:
            observations.append({'label': '射门次数（本队在前）', 'observed': f'{a:g} : {b:g}'})
        teams[side] = {'checks': [], 'observations': observations,
                       'summary': '；'.join(f'{item["label"]}：{item["observed"]}' for item in observations)}
    return {'status': '已复核', 'checkedAt': row['updatedAt'], 'source': row['source'], 'teams': teams,
            'summary': '这里只记录结果与表现，不评价争胜或保平心态是否得到支持。'}


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
