"""Optional bounded retrieval from public snapshots for interactive questions."""
import json
import re
from pathlib import Path
from pydantic import BaseModel, ConfigDict, JsonValue
from .files import PUBLIC


class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True)
    title: str
    url: str
    updatedAt: str
    data: JsonValue


def load(path: Path) -> dict[str, JsonValue]:
    if not path.is_file() or path.stat().st_size > 16000000:
        return {}
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def relevance(question: str, text: str) -> int:
    text = text.lower()
    words = re.findall(r'[a-zA-Z0-9.]{2,}|[\u4e00-\u9fff]{2,}', question.lower())
    tokens = set()
    for word in words:
        tokens.add(word)
        if re.fullmatch(r'[\u4e00-\u9fff]+', word):
            tokens.update(word[i:i+2] for i in range(len(word)-1))
    return sum(min(len(token), 8) for token in tokens if token in text)


def retrieve(question: str) -> list[Evidence]:
    candidates: list[tuple[int, Evidence]] = []
    def add(title: str, url: str, stamp: str, value: JsonValue) -> None:
        text = json.dumps(value, ensure_ascii=False)
        score = relevance(question, title + text[:8000])
        if score:
            # Large event records are shortened, with truncation explicit to the model.
            data = value if len(text) <= 6000 else {'excerpt': text[:6000], 'truncated': True}
            candidates.append((score, Evidence(title=title, url=url, updatedAt=stamp, data=data)))
    daily = load(PUBLIC / 'daily-football.json')
    for row in daily.get('matches', []):
        teams = row.get('teams', {})
        names = ' vs '.join(str(teams.get(s, {}).get('label') or teams.get(s, {}).get('name') or '') for s in ['home', 'away'])
        value = {k: row.get(k) for k in ['competition', 'kickoff', 'state', 'teams', 'events', 'scoreScope', 'venue', 'source', 'updatedAt']}
        add(names, 'https://inwesting.shop/#/live', str(daily.get('checkedAt') or daily.get('updatedAt') or ''), value)
    meetings = load(PUBLIC / 'racing' / 'meetings.json')
    for row in meetings.get('races', []):
        ident = str(row.get('id', ''))
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}-(ST|HV)-\d{1,2}', ident):
            continue
        value = load(PUBLIC / 'racing' / 'races' / (ident + '.json')) or row
        add(str(row.get('date', ''))+' '+str(row.get('courseName', ''))+' 第'+str(row.get('raceNo', ''))+'场',
            'https://inwesting.shop/#/race/'+ident, str(value.get('updatedAt') or meetings.get('updatedAt') or ''), value)
    for filename, key in [('quotes', 'quotes'), ('assets', 'assets')]:
        data = load(PUBLIC / 'finance' / (filename+'.json'))
        entries = data.get(key, {})
        items = entries.values() if isinstance(entries, dict) else entries
        for value in items:
            if isinstance(value, dict):
                add(str(value.get('name') or value.get('label') or value.get('code') or value.get('symbol') or '市场行情'),
                    'https://inwesting.shop/#/markets', str(data.get('updatedAt') or ''), value)
    stocks = load(PUBLIC / 'finance' / 'stocks.json')
    for stock in stocks.get('stocks', []):
        if relevance(question, str(stock.get('name', ''))+' '+str(stock.get('code', ''))) >= 2:
            add(str(stock.get('name', '')), 'https://inwesting.shop/#/stock/'+str(stock.get('code', '')),
                str(stocks.get('updatedAt') or ''), stock)
    chosen, size = [], 0
    for _, item in sorted(candidates, key=lambda row: -row[0]):
        length = len(item.model_dump_json())
        if size + length <= 18000:
            chosen.append(item); size += length
        if len(chosen) == 8:
            break
    return chosen
