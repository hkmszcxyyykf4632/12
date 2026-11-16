"""Fill missing names from paired Chinese variants of current club roster tables."""
import re
import unicodedata
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError

from .files import PUBLIC, fetch_text, publish
from .live import Catalogue
from .leagues import league_path
from .names import NameSnapshot, PlayerName, Players, candidates, lookup_batch

ARTICLES = {'Arsenal':'Arsenal F.C.','Aston Villa':'Aston Villa F.C.','Bournemouth':'AFC Bournemouth',
    'Brentford':'Brentford F.C.','Brighton':'Brighton & Hove Albion F.C.','Chelsea':'Chelsea F.C.',
    'Coventry City':'Coventry City F.C.','Crystal Palace':'Crystal Palace F.C.','Everton':'Everton F.C.',
    'Fulham':'Fulham F.C.','Hull City':'Hull City A.F.C.','Ipswich Town':'Ipswich Town F.C.',
    'Leeds':'Leeds United F.C.','Liverpool':'Liverpool F.C.','Man City':'Manchester City F.C.',
    'Man Utd':'Manchester United F.C.','Newcastle':'Newcastle United F.C.',
    "Nott'm Forest":'Nottingham Forest F.C.','Spurs':'Tottenham Hotspur F.C.','Sunderland':'Sunderland A.F.C.'}


class ArticleHTML(BaseModel):
    text: str


class ParsedArticle(BaseModel):
    parse: ArticleHTML


def normalized(value: str) -> str:
    value = re.sub(r'\s*\([^)]*\)', '',value)
    value = unicodedata.normalize('NFKD',value).casefold()
    return re.sub(r'[^a-z0-9]', '',value)


def roster_names(markup: str) -> dict[str,str]:
    soup = BeautifulSoup(markup,'html.parser')
    found = {}
    for table in soup.find_all('table'):
        classes = table.get('class') or []
        if any('infobox' in str(value) for value in classes):
            continue
        if any('navbox' in str(value) for value in classes) and not table.select_one('.agent.vcard'):
            continue
        for cell in table.find_all('td'):
            if cell.find('table'):
                continue
            for alias in cell.select('.ilh-all[data-lang-code="en"]'):
                label = alias.select_one('.ilh-page')
                english = str(alias.get('data-foreign-title',''))
                if label and english:
                    anchor = label.find('a')
                    chinese = str(anchor.get('title', '')) if anchor else ''
                    chinese = re.sub(r'[（(](页面不存在|頁面不存在|page does not exist)[）)]$', '', chinese).strip()
                    chinese = chinese or label.get_text(' ',strip=True)
                    if re.search(r'[\u3400-\u9fff]',chinese):
                        found.setdefault(normalized(english),chinese)
            text = cell.get_text(' ',strip=True)
            match = re.search(r'[（(]([A-Za-zÀ-ž][A-Za-zÀ-ž\s.\-’\x27]+)[）)]',text)
            if match:
                prefix = re.split(r'[（(]',text,maxsplit=1)[0].strip()
                if re.search(r'[\u3400-\u9fff]',prefix) and len(prefix)<70:
                    found.setdefault(normalized(match.group(1)),prefix)
    return found


def load_variants(item: tuple[int,str]) -> tuple[int,str,dict[str,str],dict[str,str]]:
    team_id,title = item
    variants=[]
    for variant in ['zh-cn','zh-hk']:
        params={'action':'parse','page':title,'prop':'text','variant':variant,'format':'json','formatversion':'2','maxlag':'5'}
        response=ParsedArticle.model_validate_json(fetch_text('https://zh.wikipedia.org/w/api.php?'+urllib.parse.urlencode(params)))
        variants.append(roster_names(response.parse.text))
    return team_id,title,variants[0],variants[1]


def matched_roster_name(player, mandarin: dict[str, str], cantonese: dict[str, str]) -> tuple[str | None, str]:
    labels = candidates(player)
    keys = [normalized(value) for value in labels]
    exact = next((key for key in keys if key in mandarin and key in cantonese), None)
    if exact:
        return exact, 'Current club roster and exact English name'
    prefixes = [normalized(label) for label in labels if len(label.split()) >= 2 and len(normalized(label)) >= 9]
    matches = {key for key in mandarin if key in cantonese and any(key.startswith(prefix) for prefix in prefixes)}
    if len(matches) == 1:
        return matches.pop(), 'Current club roster and unique full-name prefix including Spanish surnames'
    return None, ''


def refresh_club_names(league: str = 'epl') -> NameSnapshot:
    folder = league_path(PUBLIC, league)
    articles = ARTICLES
    if league == 'laliga':
        from .laliga import CLUBS
        articles = {values[0]: values[3] for values in CLUBS.values()}
    elif league == 'ucl':
        import json
        articles = {team['name']: team['article'] for team in json.loads((folder / 'data.json').read_text(encoding='utf-8'))['teams']}
    raw=(folder/'data.json').read_text(encoding='utf-8')
    catalogue=Catalogue.model_validate_json(raw)
    roster=Players.model_validate_json(raw)
    snapshot=NameSnapshot.model_validate_json((folder/'names.json').read_text(encoding='utf-8'))
    titles = [articles[t.name] for t in catalogue.teams if t.name in articles]
    pages = {}
    for offset in range(0, len(titles), 20):
        pages.update(lookup_batch(titles[offset:offset + 20]))
    tasks=[]
    for team in catalogue.teams:
        page=pages.get(articles.get(team.name,''))
        chinese=next((link.title for link in page.langlinks if link.lang=='zh'),None) if page else None
        if chinese:
            tasks.append((team.id,chinese))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(load_variants,item) for item in tasks]
        for future in futures:
            try:
                team_id,title,mandarin,cantonese=future.result()
            except (OSError,urllib.error.URLError,ValidationError):
                continue
            for player in roster.players:
                if str(player.code) in snapshot.names:
                    continue
                if player.team!=team_id:
                    continue
                key, matched_by = matched_roster_name(player, mandarin, cantonese)
                if key:
                    snapshot.names[str(player.code)]=PlayerName(code=player.code,english=f'{player.first_name} {player.second_name}',
                        mandarin=mandarin[key],cantonese=cantonese[key],
                        mandarinSource='https://zh.wikipedia.org/zh-cn/'+urllib.parse.quote(title),
                        cantoneseSource='https://zh.wikipedia.org/zh-hk/'+urllib.parse.quote(title),
                        matchedBy=matched_by,checkedAt=datetime.now(timezone.utc).isoformat())
    snapshot.updatedAt=datetime.now(timezone.utc).isoformat()
    snapshot.unresolved=[p.code for p in roster.players if str(p.code) not in snapshot.names]
    publish(folder/'names.json',snapshot.model_dump(mode='json'))
    return snapshot
