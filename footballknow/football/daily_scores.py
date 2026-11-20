"""Daily worldwide scoreboards, with bounded polling and persistent pre-match records."""
import json
import math
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from .files import PUBLIC, STATE, fetch_text, publish, read_json
from .leagues import LEAGUES, league_path
from .motivation import attach_research
from .market_odds import line_value
from .odds import american

HK = timezone(timedelta(hours=8))
BASE = 'https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard'
OUTPUT = PUBLIC / 'daily-football.json'
LOCAL_IDS = {'700': 'epl', '740': 'laliga', '730': 'seriea', '720': 'bundesliga', '775': 'ucl'}
FRENCH_NAMES = {'Paris Saint-Germain': '巴黎圣日耳曼', 'Nice': '尼斯', 'AS Monaco': '摩纳哥',
                'AJ Auxerre': '欧塞尔', 'Toulouse': '图卢兹', 'Lens': '朗斯', 'Lyon': '里昂',
                'Lille': '里尔', 'Brest': '布雷斯特', 'Strasbourg': '斯特拉斯堡',
                'Marseille': '马赛', 'Rennes': '雷恩', 'Nantes': '南特', 'Le Havre AC': '勒阿弗尔',
                'Angers': '昂热', 'Paris FC': '巴黎FC', 'Metz': '梅斯', 'Lorient': '洛里昂',
                'Saint-Etienne': '圣埃蒂安', 'Reims': '兰斯', 'Montpellier': '蒙彼利埃'}
COMPETITIONS = {
    'English Premier League': '英超', 'Premier League': '英超', 'LALIGA': '西甲',
    'Italian Serie A': '意甲', 'Serie A': '意甲', 'Bundesliga': '德甲', 'Ligue 1': '法甲',
    'UEFA Champions League': '欧冠', 'UEFA Europa League': '欧联杯',
    'UEFA Conference League': '欧协联', 'UEFA Nations League': '欧国联',
    'UEFA European Championship': '欧洲杯', 'UEFA European Championship Qualifying': '欧洲杯预选赛',
    'FIFA World Cup': '世界杯', 'FIFA U-17 World Cup': 'U17世界杯', 'FIFA U-20 World Cup': 'U20世界杯',
    'FIFA World Cup Qualifying - UEFA': '世界杯欧洲区预选赛',
    'FIFA World Cup Qualifying - CONMEBOL': '世界杯南美区预选赛',
    'FIFA World Cup Qualifying - AFC': '世界杯亚洲区预选赛',
    'FIFA World Cup Qualifying - CAF': '世界杯非洲区预选赛',
    'FIFA World Cup Qualifying - Concacaf': '世界杯中北美区预选赛',
    'International Friendly': '国际友谊赛', "Women's International Friendly": '女子国际友谊赛',
    "UEFA Women's Champions League": '女子欧冠', 'English FA Cup': '英格兰足总杯',
    'English Carabao Cup': '英格兰联赛杯', 'Copa del Rey': '西班牙国王杯',
    'Coppa Italia': '意大利杯', 'German DFB Pokal': '德国杯', 'Coupe de France': '法国杯',
    'English League Championship': '英冠', 'EFL Championship': '英冠', 'EFL League One': '英甲',
    'EFL League Two': '英乙', 'National League': '英格兰全国联赛', 'LALIGA 2': '西乙',
    '2. Bundesliga': '德乙', 'Italian Serie B': '意乙', 'Ligue 2': '法乙',
    'Dutch Eredivisie': '荷甲', 'Eredivisie': '荷甲', 'Keuken Kampioen Divisie': '荷乙',
    'Portuguese Primeira Liga': '葡超', 'Liga Portugal': '葡超', 'Taca de Portugal': '葡萄牙杯',
    'Belgian Pro League': '比甲', 'Danish Superliga': '丹麦超', 'Norwegian Eliteserien': '挪超',
    'Scottish Premiership': '苏超', 'SPFL Championship': '苏冠', 'Russian Premier': '俄超',
    'Turkish Super Lig': '土超', 'Swiss Super League': '瑞士超', 'Austrian Bundesliga': '奥甲',
    'MLS': '美职联', 'Major League Soccer': '美职联', 'Liga MX': '墨西哥超',
    'Brazilian Serie A': '巴西甲', 'Argentine LPF': '阿根廷甲', 'Chilean Primera': '智利甲',
    'Colombian Primera A': '哥伦比亚甲', 'LigaPro Ecuador': '厄瓜多尔甲',
    'Liga AUF Uruguaya': '乌拉圭甲', 'Paraguayan Primera': '巴拉圭甲', 'Liga FPD': '哥斯达黎加甲',
    'CONMEBOL Libertadores': '南美解放者杯', 'CONMEBOL Sudamericana': '南美杯',
    'Japanese J1 League': '日本J1', 'Japanese J2 League': '日本J2', 'Chinese Super League': '中超',
    'A-League Men': '澳超', 'A-League Women': '澳女联', 'Saudi Pro League': '沙特联',
    'Indian Super League': '印度超', 'Indian Football League': '印度甲',
    'AFC Champions League Elite': '亚冠精英联赛', 'AFC Champions League Two': '亚冠二级联赛',
    'AFC Asian Cup': '亚洲杯', 'Africa Cup of Nations': '非洲杯', 'Copa América': '美洲杯',
    'NCAAW Soccer': '美国大学女子足球', 'NCAA Soccer': '美国大学足球', 'Première Ligue': '法国女足甲级',
    'Brazil Serie A': '巴西甲', 'Club Friendly': '俱乐部友谊赛', 'Copa Bolivia': '玻利维亚杯',
    'Copa de la Reina': '西班牙王后杯', 'Liga F': '西班牙女足甲级', 'NCAAM Soccer': '美国大学男子足球',
    'Peru Liga 1': '秘鲁甲', 'SPFL Premiership': '苏超', 'Swedish Allsvenskan': '瑞典超',
    'Swedish Allsvenskan Pro/Rel': '瑞典超升降级附加赛', "Women's Super League": '英格兰女足超级联赛',
    'WSL Players Cup': '英格兰女足联赛杯',
}
STATUS = {
    'STATUS_SCHEDULED': ('scheduled', '未开赛'), 'STATUS_IN_PROGRESS': ('live', '进行中'),
    'STATUS_HALFTIME': ('live', '中场休息'), 'STATUS_END_PERIOD': ('live', '节间休息'),
    'STATUS_FULL_TIME': ('finished', '已完场'), 'STATUS_FINAL': ('finished', '已完场'),
    'STATUS_FINAL_AET': ('finished', '加时完场'), 'STATUS_FINAL_PEN': ('finished', '点球决胜完场'),
    'STATUS_POSTPONED': ('postponed', '延期'), 'STATUS_CANCELED': ('cancelled', '取消'),
    'STATUS_CANCELLED': ('cancelled', '取消'), 'STATUS_ABANDONED': ('abandoned', '腰斩'),
    'STATUS_SUSPENDED': ('suspended', '暂停'), 'STATUS_DELAYED': ('delayed', '延迟开赛'),
}


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed if parsed.tzinfo else None
    except (ValueError, TypeError):
        return None


def load(path):
    try:
        return read_json(path)
    except (OSError, ValueError):
        return {}


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) and result >= 0 else None
    except (TypeError, ValueError):
        return None


def identities():
    names, contexts = {}, {}
    for league in LEAGUES:
        folder = league_path(PUBLIC, league)
        data, table, live = (load(folder / f'{name}.json') for name in ('data', 'standings', 'live'))
        contexts[league] = {'data': data, 'table': table, 'live': live, 'news': load(folder / 'news.json')}
        for team in [*data.get('teams', []), *table.get('entries', [])]:
            if team.get('espnId'):
                names[str(team['espnId'])] = {'name': team['name'], 'label': team.get('cn') or team['name']}
    return names, contexts


def scoreboard_quotes(comp, ident, stamp, started):
    result = []
    for quote in comp.get('odds') or []:
        if not isinstance(quote, dict):
            continue
        provider = (quote.get('provider') or {}).get('name')
        if not provider:
            continue
        for phase, label in [('open', 'opening'), ('close', 'latest')]:
            for field, market, keys in [
                    ('pointSpread', 'asian-handicap', {'H': 'home', 'A': 'away'}),
                    ('total', 'total-goals', {'O': 'over', 'U': 'under'}),
                    ('moneyline', '90-minute-1x2', {'H': 'home', 'D': 'draw', 'A': 'away'})]:
                values = {key: (((quote.get(field) or {}).get(side) or {}).get(phase) or {}) for key, side in keys.items()}
                prices = {key: american(value.get('odds')) for key, value in values.items()}
                line = None
                if market == 'asian-handicap':
                    line, away = line_value(values['H'].get('line')), line_value(values['A'].get('line'))
                    if line is None or away is None or line != -away:
                        continue
                if market == 'total-goals':
                    line = line_value(values['O'].get('line'))
                    if line is None or line < 0 or line != line_value(values['U'].get('line')):
                        continue
                if all(prices.values()):
                    result.append({'market': market, 'provider': provider, 'via': 'ESPN',
                                   'phase': label, 'line': line, 'prices': prices, 'kind': 'bookmaker',
                                   'fetchedAt': stamp, 'quotedAt': None, 'inPlay': started and label == 'latest',
                                   'source': f'https://www.espn.com/soccer/odds/_/gameId/{ident}'})
    return result


def preserve_pregame_quotes(row, previous):
    if not previous or previous.get('kickoff') != row['kickoff'] or any(
            previous.get('teams', {}).get(side, {}).get('id') != row['teams'][side]['id'] for side in ['home', 'away']):
        previous = {}
    kickoff = timestamp(row['kickoff'])
    key = lambda q: (q.get('market'), q.get('provider'), q.get('via'))
    opening, last_pre = {}, {}
    for quote in sorted(previous.get('quotes', []), key=lambda q: q.get('fetchedAt', '')):
        if quote.get('phase') == 'opening':
            opening.setdefault(key(quote), quote)
        stamp = timestamp(quote.get('fetchedAt'))
        if quote.get('phase') == 'latest' and not quote.get('inPlay') and stamp and stamp < kickoff:
            last_pre[key(quote)] = quote
    fresh = []
    for quote in row.get('quotes', []):
        quote = dict(quote)
        if quote.get('phase') == 'opening':
            opening.setdefault(key(quote), quote)
            continue
        stamp = timestamp(quote.get('fetchedAt'))
        if quote.get('phase') == 'latest':
            quote['inPlay'] = bool(row['started'] or not stamp or stamp >= kickoff)
            if not quote['inPlay']:
                saved_stamp = timestamp(last_pre.get(key(quote), {}).get('fetchedAt'))
                if not saved_stamp or stamp >= saved_stamp:
                    last_pre[key(quote)] = quote
                continue
        fresh.append(quote)
    for quote in last_pre.values():
        saved = dict(quote)
        if row['started'] or (timestamp(row.get('updatedAt')) or kickoff) >= kickoff:
            saved['lastPregame'] = True
        fresh.append(saved)
    row['quotes'] = list(opening.values()) + fresh
    return row


def parse_event(event, source_day, stamp, names):
    ident = str(event.get('id', ''))
    if not re.fullmatch(r'\d{1,16}', ident):
        raise ValueError('Invalid daily event identity')
    comp = event['competitions'][0]
    sides = {c['homeAway']: c for c in comp['competitors']}
    if set(sides) != {'home', 'away'}:
        raise ValueError('Missing daily event opponent')
    kickoff = timestamp(comp.get('date') or event.get('date'))
    if not kickoff:
        raise ValueError('Daily event has no timezone-aware kickoff')
    match = re.search(r'~l:(\d+)', event.get('uid', ''))
    if not match:
        raise ValueError('Missing competition identity')
    competition_id = match[1]
    raw_label = (comp.get('altGameNote') or event.get('season', {}).get('slug') or '赛事').split(',')[0].strip()
    status = comp.get('status') or event.get('status') or {}
    kind = status.get('type', {})
    state, label = STATUS.get(kind.get('name'),
                             ('finished', '已完场') if kind.get('completed') else
                             ('live', '进行中') if kind.get('state') == 'in' else ('scheduled', '未开赛'))
    started = state in {'live', 'finished', 'suspended', 'abandoned'}
    teams = {}
    for side, c in sides.items():
        team = c['team']
        code = str(team['id'])
        known = names.get(code, {})
        stats = {s['name']: number(s.get('displayValue', s.get('value'))) for s in c.get('statistics', []) if s.get('name')}
        goals = number(c.get('score')) if started else None
        teams[side] = {'id': code, 'name': known.get('name', team['displayName']),
                       'label': known.get('label', FRENCH_NAMES.get(team['displayName'], team['displayName']) if competition_id == '710' else team['displayName']), 'originalName': team['displayName'],
                       'form': c.get('form') if re.fullmatch('[WDL]{1,10}', c.get('form') or '') else '',
                       'goals': int(goals) if goals is not None and goals.is_integer() and goals <= 99 else None,
                       'shots': stats.get('totalShots'), 'shotsOnTarget': stats.get('shotsOnTarget'),
                       'possession': stats.get('possessionPct')}
    if teams['home']['id'] == teams['away']['id']:
        raise ValueError('Duplicate daily event opponents')
    events = []
    for detail in comp.get('details', []):
        type_name = str(detail.get('type', {}).get('text', ''))
        event_kind = ('进球' if detail.get('scoringPlay') else '红牌' if detail.get('redCard') else
                      '黄牌' if detail.get('yellowCard') else '换人' if 'substitution' in type_name.lower() else type_name)
        events.append({'kind': event_kind, 'clock': detail.get('clock', {}).get('displayValue', ''),
                       'teamId': str(detail.get('team', {}).get('id', '')),
                       'players': [p.get('displayName', '') for p in detail.get('athletesInvolved', [])],
                       'ownGoal': bool(detail.get('ownGoal')), 'penalty': bool(detail.get('penaltyKick'))})
    extra = (status.get('period') or 0) > 2 or any(x in kind.get('name', '') for x in ('AET', 'PEN', 'EXTRA'))
    return {'id': ident, 'competitionId': competition_id, 'league': LOCAL_IDS.get(competition_id),
            'competition': COMPETITIONS.get(raw_label, raw_label), 'competitionOriginal': raw_label,
            'season': event.get('season', {}).get('year'), 'kickoff': kickoff.isoformat(),
            'day': kickoff.astimezone(HK).date().isoformat(), 'state': state, 'status': label,
            'clock': status.get('displayClock', '') if state == 'live' else '',
            'started': started, 'finished': state == 'finished', 'teams': teams, 'events': events,
            'scoreScope': '含加时或点球阶段' if extra else '90分钟含补时',
            'neutral': bool(comp.get('neutralSite')), 'venue': comp.get('venue') or event.get('venue') or {},
            'quotes': scoreboard_quotes(comp, ident, stamp, started), 'updatedAt': stamp, 'sourceDay': source_day,
            'source': f'https://www.espn.com/soccer/match/_/gameId/{ident}',
            'feedSource': f'{BASE}?dates={source_day.replace("-", "")}&limit=1000'}


def fetch_day(day, stamp, names):
    url = f'{BASE}?dates={day.replace("-", "")}&limit=1000'
    raw = json.loads(fetch_text(url))
    events = raw.get('events')
    if not isinstance(events, list) or len(events) >= 1000:
        raise ValueError('Daily scoreboard missing or possibly truncated')
    rows = [parse_event(e, day, stamp, names) for e in events]
    if len({m['id'] for m in rows}) != len(rows):
        raise ValueError('Duplicate daily scoreboard identities')
    return rows


def refresh_daily(at=None, fetcher=fetch_day):
    at = at or datetime.now(timezone.utc)
    stamp, today = at.isoformat(), at.astimezone(HK).date()
    first, last = (today - timedelta(days=1)).isoformat(), (today + timedelta(days=1)).isoformat()
    oldest = (today - timedelta(days=30)).isoformat()
    previous = load(OUTPUT)
    names, contexts = identities()
    rows = {m['id']: m for m in previous.get('matches', []) if oldest <= m['day'] <= last}
    source_days = {d: v for d, v in previous.get('sourceDays', {}).items() if d >= oldest}
    errors, success = [], 0
    # ESPN's daily bucket straddles UTC midnight. Four source dates cover three HK dates.
    days = [(today + timedelta(days=offset)).isoformat() for offset in (-2, -1, 0, 1)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [(day, pool.submit(fetcher, day, stamp, names)) for day in days]
        for day, future in jobs:
            try:
                incoming = future.result()
                for row in incoming:
                    if first <= row['day'] <= last:
                        rows[row['id']] = preserve_pregame_quotes(row, rows.get(row['id']))
                source_days[day] = {'updatedAt': stamp, 'ok': True}
                success += 1
            except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
                source_days[day] = {**source_days.get(day, {}), 'ok': False}
                errors.append({'day': day, 'message': '来源暂时不可用，保留最近成功资料'})
    ordered = sorted(rows.values(), key=lambda row: (row['kickoff'], row['id']))
    for row in ordered:
        attach_research(row, ordered, contexts, at, STATE / 'daily-motivation')
        context = contexts.get(row.get('league'), {})
        club_ids = {t['id'] for t in context.get('data', {}).get('teams', [])
                    if t['name'] in [row['teams'][s]['name'] for s in ('home', 'away')]}
        cutoff = min(at, timestamp(row['kickoff']))
        row['relatedNews'] = [a for a in context.get('news', {}).get('articles', [])
                              if club_ids.intersection(a.get('teamIds', [])) and timestamp(a.get('publishedAt'))
                              and cutoff - timedelta(days=7) <= timestamp(a['publishedAt']) <= cutoff][:6]
    result = {'version': 1, 'timezone': 'Asia/Hong_Kong', 'refreshSeconds': 60,
              'updatedAt': stamp if success else previous.get('updatedAt'), 'checkedAt': stamp,
              'window': {'from': first, 'to': last}, 'sourceDays': source_days, 'errors': errors,
              'provider': 'ESPN 全球足球比分', 'matches': ordered,
              'coverage': '全球主要联赛、杯赛及国家队赛事，以 ESPN 当日收录为准；即时检查昨天、今天、明天，已收录记录保留30天。'}
    publish(OUTPUT, result)
    if errors:
        raise OSError(f'Daily football: {success}/4 source dates refreshed; previous records retained')
    return result
