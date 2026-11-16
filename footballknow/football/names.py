"""Resolve footballers to independently labelled Chinese Wikipedia variants."""
import html
import re
import time
import urllib.error
import urllib.parse
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from typing import Final

from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .files import PUBLIC, fetch_text, publish
from .leagues import league_path

EN_API: Final = 'https://en.wikipedia.org/w/api.php?'
ZH_API: Final = 'https://zh.wikipedia.org/w/api.php?'


class Player(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    code: int
    team: int = 0
    first_name: str
    second_name: str
    web_name: str
    known_name: str | None = None
    birth_date: str | None = None


class Players(BaseModel):
    model_config = ConfigDict(frozen=True)
    season: str
    players: list[Player]


class LanguageLink(BaseModel):
    lang: str
    title: str


class WikiPage(BaseModel):
    title: str
    extract: str = ''
    langlinks: list[LanguageLink] = Field(default_factory=list)


class TitleChange(BaseModel):
    original: str = Field(alias='from')
    to: str


class WikiQuery(BaseModel):
    pages: list[WikiPage] = Field(default_factory=list)
    normalized: list[TitleChange] = Field(default_factory=list)
    redirects: list[TitleChange] = Field(default_factory=list)


class WikiResponse(BaseModel):
    query: WikiQuery


class ParsedTitle(BaseModel):
    displaytitle: str


class TitleResponse(BaseModel):
    parse: ParsedTitle


class PlayerName(BaseModel):
    model_config = ConfigDict(frozen=True)
    code: int
    english: str
    mandarin: str
    cantonese: str
    mandarinSource: str
    cantoneseSource: str
    matchedBy: str = 'English article and exact birth date'
    checkedAt: str


class NameSnapshot(BaseModel):
    version: int = 1
    updatedAt: str
    season: str
    total: int
    names: dict[str, PlayerName] = Field(default_factory=dict)
    unresolved: list[int] = Field(default_factory=list)
    attempted: dict[str, str] = Field(default_factory=dict)
    attribution: str = 'Wikipedia contributors; name variants from zh-cn and zh-hk pages, CC BY-SA 4.0'


def candidates(player: Player) -> list[str]:
    first = (player.first_name or player.web_name).split()[0]
    short = re.sub(r'^[A-Z]\.', '', player.web_name)
    names = list(dict.fromkeys(filter(None, [
        player.known_name, f'{player.first_name} {player.second_name}',
        f'{first} {short}', f'{first} {(player.second_name.split() or [short])[0]}',
        f'{first} {short} (footballer)',
    ])))
    if player.birth_date:
        common = player.known_name or f'{first} {short}'
        names.append(f'{common} (footballer, born {player.birth_date[:4]})')
    return names


def lookup_batch(titles: list[str]) -> dict[str, WikiPage]:
    params = {'action':'query', 'titles':'|'.join(titles), 'prop':'extracts|langlinks',
              'exintro':'1', 'explaintext':'1', 'exlimit':'20', 'lllang':'zh', 'lllimit':'max',
              'redirects':'1', 'format':'json', 'formatversion':'2', 'maxlag':'5'}
    response = WikiResponse.model_validate_json(fetch_text(EN_API + urllib.parse.urlencode(params)))
    pages = {page.title: page for page in response.query.pages}
    aliases = {item.original:item.to for item in response.query.normalized + response.query.redirects}
    found = {}
    for title in titles:
        current = title
        for _ in range(5):
            if current not in aliases:
                break
            current = aliases[current]
        if current in pages:
            found[title] = pages[current]
    return found


def birth_matches(player: Player, page: WikiPage) -> bool:
    if not player.birth_date:
        return False
    born = date.fromisoformat(player.birth_date)
    spellings = [f'{born.day} {born:%B %Y}', f'{born:%B} {born.day}, {born.year}', born.isoformat()]
    extract = re.sub(r'\s+', ' ', page.extract)
    def normalized(value):
        return ' '.join(re.sub(r'[^a-z0-9]+', ' ', unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower()).split())
    lead = ' ' + normalized(re.split(r'\(born|\bis an?\b', extract[:200], maxsplit=1)[0]) + ' '
    title = normalized(re.sub(r'\s*\(.*', '', page.title))
    name_matches = any(normalized(name) == title or ' ' + normalized(name) + ' ' in lead for name in candidates(player))
    return name_matches and any(value in extract for value in spellings)


def search_player(player: Player) -> str | None:
    if not player.birth_date:
        return None
    query = f'{player.known_name or player.web_name} {player.birth_date[:4]} football'
    params = {'action':'query', 'generator':'search', 'gsrsearch':query, 'gsrnamespace':'0',
              'gsrlimit':'3', 'prop':'extracts|langlinks', 'exintro':'1', 'explaintext':'1',
              'exlimit':'20', 'lllang':'zh', 'lllimit':'max', 'format':'json', 'formatversion':'2', 'maxlag':'5'}
    try:
        response = WikiResponse.model_validate_json(fetch_text(EN_API + urllib.parse.urlencode(params)))
        for page in response.query.pages:
            if birth_matches(player, page):
                chinese = next((link.title for link in page.langlinks if link.lang == 'zh'), None)
                if chinese:
                    return chinese
    except (OSError, urllib.error.URLError, ValidationError):
        return None
    return None


def translate_title(title: str, variant: str) -> str:
    params = {'action':'parse', 'page':title, 'prop':'displaytitle', 'variant':variant,
              'format':'json', 'maxlag':'5'}
    response = TitleResponse.model_validate_json(fetch_text(ZH_API + urllib.parse.urlencode(params)))
    value = BeautifulSoup(response.parse.displaytitle, 'html.parser').get_text(' ', strip=True)
    value = re.sub(r'\s*[（(][^）)]*[）)]$', '', html.unescape(value))
    if not re.search(r'[\u3400-\u9fff]', value):
        raise OSError('Chinese article has no translated display title')
    return value


def localize_player(match: tuple[Player, str]) -> PlayerName | None:
    player, title = match
    try:
        mandarin = translate_title(title, 'zh-cn')
        time.sleep(0.25)
        cantonese = translate_title(title, 'zh-hk')
        return PlayerName(code=player.code, english=f'{player.first_name} {player.second_name}',
                          mandarin=mandarin, cantonese=cantonese,
                          mandarinSource='https://zh.wikipedia.org/zh-cn/' + urllib.parse.quote(title),
                          cantoneseSource='https://zh.wikipedia.org/zh-hk/' + urllib.parse.quote(title),
                          checkedAt=datetime.now(timezone.utc).isoformat())
    except (OSError, urllib.error.URLError, ValidationError):
        return None


def refresh_names(limit: int = 60, league: str = 'epl') -> NameSnapshot:
    folder = league_path(PUBLIC, league)
    roster = Players.model_validate_json((folder / 'data.json').read_text(encoding='utf-8'))
    path = folder / 'names.json'
    snapshot = NameSnapshot(updatedAt=datetime.now(timezone.utc).isoformat(), season=roster.season, total=len(roster.players))
    if path.exists():
        previous = NameSnapshot.model_validate_json(path.read_text(encoding='utf-8'))
        active_codes = {str(player.code) for player in roster.players}
        snapshot.names = {key:value for key,value in previous.names.items() if key in active_codes}
        sources = {}
        for key, value in snapshot.names.items():
            if value.matchedBy == 'English article and exact birth date':
                sources.setdefault(value.mandarinSource, []).append(key)
        ambiguous = {key for keys in sources.values() if len(keys) > 1 for key in keys}
        snapshot.names = {key:value for key,value in snapshot.names.items() if key not in ambiguous}
        snapshot.attempted = previous.attempted
    pending = sorted([player for player in roster.players if str(player.code) not in snapshot.names],
                     key=lambda player:snapshot.attempted.get(str(player.code), ''))[:limit]
    titles = list(dict.fromkeys(title for player in pending for title in candidates(player)))
    pages: dict[str, WikiPage] = {}
    for offset in range(0, len(titles), 20):
        try:
            pages.update(lookup_batch(titles[offset:offset + 20]))
        except (OSError, urllib.error.URLError, ValidationError):
            pass
        time.sleep(0.3)
    matched = []
    for player in pending:
        chinese = None
        for title in candidates(player):
            page = pages.get(title)
            if page and birth_matches(player, page):
                chinese = next((link.title for link in page.langlinks if link.lang == 'zh'), None)
                if chinese:
                    break
        if not chinese:
            chinese = search_player(player)
            time.sleep(0.3)
        snapshot.attempted[str(player.code)] = datetime.now(timezone.utc).isoformat()
        if chinese:
            matched.append((player, chinese))
    with ThreadPoolExecutor(max_workers=2) as pool:
        for index, result in enumerate(pool.map(localize_player, matched)):
            if result:
                snapshot.names[str(result.code)] = result
            if index % 20 == 0:
                snapshot.unresolved = [p.code for p in roster.players if str(p.code) not in snapshot.names]
                publish(path, snapshot.model_dump(mode='json'))
    snapshot.updatedAt = datetime.now(timezone.utc).isoformat()
    snapshot.unresolved = [p.code for p in roster.players if str(p.code) not in snapshot.names]
    publish(path, snapshot.model_dump(mode='json'))
    return snapshot
