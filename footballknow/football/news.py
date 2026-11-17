"""News headlines with publisher timestamps and explicit team tags, without article bodies."""
from datetime import datetime, timezone
from urllib.parse import urlparse

from .files import PUBLIC, publish, read_json
from .leagues import league_path
from .rankings import COMPETITIONS, EPL_NAMES, normalize
from .ucl import fetch_json
from .news_translation import translate_titles


def parse_news(raw, catalogue):
    if not isinstance(raw.get('articles'), list):
        raise ValueError('News feed has no article list')
    rows = {}
    for article in raw['articles']:
        url = article.get('links', {}).get('web', {}).get('href', '')
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname not in {'www.espn.com', 'www.espn.co.uk', 'global.espn.com'}:
            continue
        published = article.get('published', '')
        try:
            date = datetime.fromisoformat(published.replace('Z', '+00:00'))
            if date.tzinfo is None or date > datetime.now(timezone.utc):
                continue
        except (ValueError, TypeError):
            continue
        title = str(article.get('headline', '')).strip()
        if not title:
            continue
        tagged = [c for c in article.get('categories', []) if c.get('type') == 'team' and c.get('sportId') == 600]
        team_ids = []
        for team in catalogue['teams']:
            if any(str(team.get('espnId', '')) == str(c.get('teamId')) or
                   normalize(team['name']) == normalize(EPL_NAMES.get(c.get('description'), c.get('description', '')))
                   for c in tagged):
                team_ids.append(team['id'])
        rows[url] = {'id': str(article.get('id') or url), 'title': title, 'url': url, 'publishedAt': published,
                     'source': 'ESPN', 'language': 'en', 'teamIds': team_ids,
                     'category': '转会传闻' if 'rumor' in title.lower() else '球队新闻'}
    return sorted(rows.values(), key=lambda a: a['publishedAt'], reverse=True)


def refresh_news(league):
    folder = league_path(PUBLIC, league)
    catalogue = read_json(folder / 'data.json')
    url = f'https://site.api.espn.com/apis/site/v2/sports/soccer/{COMPETITIONS[league]}/news?limit=100'
    articles = parse_news(fetch_json(url), catalogue)
    if not articles:
        raise OSError('No valid current news; retain previous snapshot')
    translation = translate_titles(articles, catalogue, league)
    result = {'version': 1, 'league': league, 'translationStatus': translation, 'updatedAt': datetime.now(timezone.utc).isoformat(),
              'intervalSeconds': 60, 'source': url, 'articles': articles}
    publish(folder / 'news.json', result)
    return result
