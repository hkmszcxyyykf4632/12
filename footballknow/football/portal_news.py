"""Chinese headline feeds for the front page; article bodies remain at their publishers."""
import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urljoin

from bs4 import BeautifulSoup

from .files import PUBLIC, fetch_text, publish
from .leagues import league_path
from .racing import load, now

FEEDS = {
    'finance': ('https://rthk.hk/rthk/news/rss/c_expressnews_cfinance.xml', '香港电台', 'news.rthk.hk'),
    'racing': ('https://racingnews.hkjc.com/chinese/feed/', '香港赛马会', 'racingnews.hkjc.com'),
    'football': ('https://rthk.hk/rthk/news/rss/c_expressnews_csport.xml', '香港电台', 'news.rthk.hk'),
}
FOOTBALL = re.compile(r'足球|英超|西甲|意甲|德甲|歐冠|欧冠|歐聯|欧联|世界盃|世界杯|歐國|欧国|曼聯|曼联|阿仙奴|阿森纳|車路士|切尔西|利物浦|曼城|皇馬|皇马|巴塞|巴萨|入球|國足|国足|港足|足總|足总|球隊|球队')


def news_image(html, base):
    soup = BeautifulSoup(html or '', 'html.parser')
    meta = soup.select_one('meta[property="og:image"]')
    candidates = ([meta.get('content')] if meta else []) + [img.get('src') for img in soup.select('img[src]')]
    for value in candidates:
        url = urljoin(base, value or '')
        parsed = urlsplit(url)
        if parsed.hostname not in {'newsstatic.rthk.hk', 'res.hkjc.com'} or not re.search(r'\.(?:jpg|jpeg|png|webp)$', parsed.path, re.I):
            continue
        if not (parsed.path.startswith('/images/mfile_') or parsed.path.startswith('/racingnews/wp-content/uploads/')):
            continue
        return 'https://' + parsed.netloc + parsed.path
    return None


def enrich_images(categories, prior):
    saved = {a['url']: a for feed in prior.get('categories', {}).values() for a in feed.get('articles', [])}
    budget = 6
    for category, feed in categories.items():
        for article in feed.get('articles', [])[:3]:
            old = saved.get(article['url'], {})
            if not article.get('imageUrl') and old.get('imageUrl'):
                article['imageUrl'] = old['imageUrl']
            if article.get('imageUrl') or category == 'racing' or old.get('imageChecked'):
                article['imageChecked'] = True
                continue
            if not budget or urlsplit(article['url']).hostname != 'news.rthk.hk':
                continue
            budget -= 1
            try:
                image = news_image(fetch_text(article['url']), article['url'])
                article['imageChecked'] = True
                if image:
                    article['imageUrl'] = image
            except (OSError, ValueError):
                pass


def parse_feed(raw, category, source, host):
    root = ET.fromstring(raw)
    rows = []
    for item in root.findall('./channel/item'):
        title = (item.findtext('title') or '').strip()
        url = (item.findtext('link') or '').strip()
        parsed = urlsplit(url)
        if parsed.hostname != host or parsed.scheme not in {'http', 'https'} or not re.search(r'[\u3400-\u9fff]', title):
            continue
        try:
            date = parsedate_to_datetime(item.findtext('pubDate') or '')
            if date.tzinfo is None or date > datetime.now(timezone.utc):
                continue
        except (TypeError, ValueError):
            continue
        if category == 'football' and not FOOTBALL.search(title):
            continue
        url = 'https://' + parsed.netloc + parsed.path + ('?' + parsed.query if parsed.query else '')
        rows.append({'id': hashlib.sha256(url.encode()).hexdigest()[:16], 'titleZh': title, 'title': title,
                     'url': url, 'publishedAt': date.isoformat(), 'source': source, 'category': category,
                     'language': 'zh', 'translated': False})
        content = item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded') or item.findtext('description') or ''
        image = news_image(content, url)
        if image:
            rows[-1]['imageUrl'] = image
    return rows


def sync_portal_news():
    prior = load(PUBLIC / 'portal-news.json')
    categories, failed = {}, []
    for category, (url, publisher, host) in FEEDS.items():
        try:
            rows = parse_feed(fetch_text(url), category, publisher, host)
            if not rows and category != 'football':
                raise ValueError('新闻列表为空。')
            categories[category] = {'articles': rows, 'checkedAt': now(), 'source': url, 'ok': True}
        except (OSError, ValueError, ET.ParseError):
            categories[category] = {**prior.get('categories', {}).get(category, {}), 'ok': False}
            failed.append(category)
    football = categories['football'].get('articles', [])
    for league in ['epl', 'laliga', 'ucl', 'seriea', 'bundesliga']:
        for article in load(league_path(PUBLIC, league) / 'news.json').get('articles', []):
            if not article.get('titleZh'):
                continue
            football.append({**article, 'category': 'football', 'translated': True, 'language': 'zh'})
    categories['football']['articles'] = football
    for item in categories.values():
        unique = {a['url']: a for a in item.get('articles', [])}
        item['articles'] = sorted(unique.values(), key=lambda a: a['publishedAt'], reverse=True)[:60]
    if not any(v.get('articles') for v in categories.values()):
        raise ValueError('新闻来源暂未返回有效中文标题。')
    enrich_images(categories, prior)
    publish(PUBLIC / 'portal-news.json', {'updatedAt': now(), 'intervalSeconds': 300, 'categories': categories, 'failed': failed})
    return sum(len(v['articles']) for v in categories.values())
