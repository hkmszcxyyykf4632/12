"""Public squad valuations, matched by birth date plus name, refreshed in small batches."""
import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from .files import PUBLIC, STATE, fetch_text, publish, read_json
from .leagues import league_path

LEAGUE_IDS = {'epl':47, 'laliga':87, 'bundesliga':54, 'seriea':55, 'ucl':42}
ORIGIN = 'https://www.fotmob.com'


def now():
    return datetime.now(timezone.utc).isoformat()


def age(stamp):
    try:
        return (datetime.now(timezone.utc)-datetime.fromisoformat(stamp.replace('Z','+00:00'))).total_seconds()
    except (ValueError, TypeError, AttributeError):
        return math.inf


def load(path):
    try:
        return read_json(path)
    except (OSError, ValueError):
        return {}


def embedded(html):
    script = BeautifulSoup(html, 'html.parser').find('script', id='__NEXT_DATA__')
    if not script:
        raise ValueError('Public squad data missing')
    return json.loads(script.string or script.get_text())['props']['pageProps']


def teams_from_page(page, expected_id):
    if page.get('details', {}).get('id') != expected_id:
        raise ValueError('Wrong league returned')
    found = {}
    def walk(value):
        if isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            ident, url = value.get('id'), value.get('pageUrl', '')
            if isinstance(ident, int) and re.fullmatch(r'/teams/'+str(ident)+r'/overview/[a-z0-9-]+', url):
                found[ident] = {'id':ident, 'name':value.get('name'), 'url':ORIGIN+url.replace('/overview/','/squad/')}
            for item in value.values():
                walk(item)
    walk(page.get('table', []))
    if not found:
        raise ValueError('No teams in league table')
    return list(found.values())


def squad_values(page, expected_id, fetched_at):
    team = next((value for value in page.get('fallback', {}).values() if isinstance(value,dict) and value.get('details',{}).get('id') == expected_id), None)
    if not team or not team.get('squad', {}).get('squad'):
        raise ValueError('Wrong or empty squad returned')
    records = []
    for group in team['squad']['squad']:
        if group.get('title') == 'coach':
            continue
        for p in group.get('members', []):
            value = p.get('transferValue')
            if isinstance(value, bool) or not isinstance(value, (float,int)) or not math.isfinite(value) or not 0 < value <= 1_000_000_000:
                continue
            if not isinstance(p.get('id'), int) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(p.get('dateOfBirth',''))):
                continue
            records.append({'sourceId':p['id'], 'name':p['name'], 'birthDate':p['dateOfBirth'],
                            'amount':value, 'currency':'EUR', 'asOf':None, 'fetchedAt':fetched_at,
                            'source':'FotMob', 'sourceUrl':ORIGIN+'/players/'+str(p['id']),
                            'team':team['details']['name'], 'kind':'estimate'})
    return records


def name_key(value):
    text = ''.join(c for c in unicodedata.normalize('NFKD', str(value or '').casefold()) if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^\w\s]', ' ', text).split())


def identity_matches(player, record):
    if not player.get('birth_date') or player['birth_date'] != record.get('birthDate'):
        return False
    candidate = name_key(record.get('name'))
    if not candidate:
        return False
    names = [player.get('known_name'), player.get('web_name'), ' '.join([player.get('first_name',''),player.get('second_name','')])]
    for value in names:
        key = name_key(value)
        if key == candidate:
            return True
        a,b = set(key.split()),set(candidate.split())
        if len(a)>=2 and len(b)>=2 and (a <= b or b <= a):
            return True
    return False


def assign_values(players, records, previous):
    values = {}
    by_birth = {}
    for r in records:
        by_birth.setdefault(r['birthDate'], {})[r['sourceId']] = r
    for p in players:
        key = str(p['code'])
        candidates = [r for r in by_birth.get(p.get('birth_date'),{}).values() if identity_matches(p,r)]
        if len(candidates)==1:
            values[key] = candidates[0]
        elif not candidates and identity_matches(p,previous.get(key,{})):
            values[key] = previous[key]
    return values


def sync_player_values(league, limit=6):
    folder = league_path(PUBLIC, league)
    catalogue, old = load(folder/'data.json'), load(folder/'player-values.json')
    cache_folder = STATE/'player-value-cache'
    team_list = load(cache_folder/(league+'-teams.json'))
    if age(team_list.get('updatedAt')) > 86400:
        try:
            page = embedded(fetch_text(ORIGIN+'/leagues/'+str(LEAGUE_IDS[league])+'/overview'))
            team_list = {'updatedAt':now(), 'teams':teams_from_page(page,LEAGUE_IDS[league])}
            publish(cache_folder/(league+'-teams.json'), team_list)
        except (OSError, ValueError, KeyError):
            pass
    records, failed, refreshed = [], [], 0
    for team in sorted(team_list.get('teams', []), key=lambda t:load(cache_folder/(str(t['id'])+'.json')).get('fetchedAt','')):
        cache_path = cache_folder/(str(team['id'])+'.json')
        cached = load(cache_path)
        if age(cached.get('fetchedAt')) > 86400 and refreshed < limit:
            refreshed += 1
            try:
                stamp = now()
                entries = squad_values(embedded(fetch_text(team['url'])),team['id'],stamp)
                if not entries:
                    raise ValueError('No published values in this squad')
                cached = {'fetchedAt':stamp, 'records':entries}
                publish(cache_path,cached)
            except (OSError, ValueError, KeyError, TypeError):
                failed.append(team['name'])
        records.extend(cached.get('records', []))
    values = assign_values(catalogue.get('players', []),records,old.get('values',{}))
    result = {'version':1, 'league':league, 'season':catalogue.get('season'), 'updatedAt':now(),
              'values':values, 'coverage':{'matched':len(values),'players':len(catalogue.get('players',[]))},
              'failedTeams':failed, 'meaning':'公开估算身价，欧元；不是成交价或FPL游戏价格。采集日期不是估值发布日期。'}
    publish(folder/'player-values.json', result)
    return result['coverage']
