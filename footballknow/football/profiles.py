"""Club identity fields with dated sources; no estimated finances."""
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import quote

from bs4 import BeautifulSoup

from .files import PUBLIC, STATE, fetch_text, publish, read_json
from .leagues import league_path
from .name_rosters import ARTICLES

FIELDS = {'full name': 'fullName', 'founded': 'founded', 'ground': 'stadium',
          'stadium': 'stadium', 'capacity': 'capacity', 'owner': 'ownership',
          'owners': 'ownership', 'ownership': 'ownership', 'chairman': 'chairman',
          'president': 'president', 'website': 'website'}
FINANCE_SOURCE = 'https://www.deloitte.com/uk/en/services/financial-advisory/analysis/deloitte-football-money-league.html'
# Revenue only, rounded EUR millions, report issued 22 January 2026 for 2024/25.
REVENUES = {'FC Barcelona': 975, 'FC Bayern Munich': 861, 'Liverpool F.C.': 836,
            'Paris Saint-Germain FC': 837, 'Manchester City F.C.': 829,
            'Manchester United F.C.': 793}


def parse_profile(markup):
    soup = BeautifulSoup(markup, 'html.parser')
    box = soup.select_one('table.infobox')
    if not box:
        raise ValueError('Club infobox missing')
    for unwanted in box.select('sup, .sortkey, .noprint, .mw-empty-elt'):
        unwanted.decompose()
    result = {}
    for row in box.find_all('tr'):
        label, value = row.find('th'), row.find('td')
        if not label or not value:
            continue
        field = FIELDS.get(label.get_text(' ', strip=True).lower())
        if not field:
            continue
        if field == 'website':
            link = value.select_one('a.external[href]')
            url = link.get('href', '') if link else ''
            if url.startswith('https://'):
                result[field] = url
        else:
            text = re.sub(r'\s+', ' ', value.get_text(' ', strip=True))
            if text:
                result[field] = text[:1200]
    if not result:
        raise ValueError('No club identity fields')
    return result


def club_profile(team):
    title = team.get('article') or ARTICLES.get(team['name'])
    if not title:
        raise ValueError('No verified club article identity')
    path = STATE / 'club-profiles' / (hashlib.sha256(title.encode()).hexdigest() + '.json')
    prior = read_json(path) if path.exists() else {}
    now = datetime.now(timezone.utc)
    if prior.get('updatedAt') and (now - datetime.fromisoformat(prior['updatedAt'])).total_seconds() < 86400:
        return prior
    source = 'https://en.wikipedia.org/wiki/' + quote(title.replace(' ', '_'))
    try:
        result = {**parse_profile(fetch_text(source)), 'source': source,
                  'updatedAt': now.isoformat(), 'sourceType': 'Wikipedia 球队资料，沿原文保留持股说明'}
    except (OSError, ValueError):
        if prior:
            return {**prior, 'refreshFailed': True}
        raise
    if title in REVENUES:
        result['financials'] = [{'metric': '营业收入', 'value': REVENUES[title], 'unit': '百万欧元',
                                'period': '2024/25', 'reportedAt': '2026-01-22',
                                'source': FINANCE_SOURCE, 'basis': '德勤报告，取整；非利润或现金余额'}]
    publish(path, result)
    return result


def refresh_profiles(league):
    folder = league_path(PUBLIC, league)
    data = read_json(folder / 'data.json')
    path = folder / 'profiles.json'
    old = read_json(path) if path.exists() else {}
    profiles = {}
    failed = []

    def run(team):
        try:
            return team['id'], club_profile(team), False
        except (OSError, ValueError):
            return team['id'], old.get('teams', {}).get(str(team['id'])), True

    with ThreadPoolExecutor(max_workers=3) as pool:
        for team_id, profile, error in pool.map(run, data['teams']):
            if profile:
                profiles[str(team_id)] = profile
            if error:
                failed.append(team_id)
    if not profiles:
        raise OSError('No club profiles available')
    result = {'version': 1, 'league': league, 'updatedAt': datetime.now(timezone.utc).isoformat(),
              'teams': profiles, 'failedTeams': failed, 'sourceCheckSeconds': 86400}
    publish(path, result)
    return result
