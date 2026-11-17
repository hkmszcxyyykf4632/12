from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import pytest
from bs4 import BeautifulSoup

from football import horse_directory as directory, racing, racing_live as live, racing_people as people
from football import portal_news as news


@pytest.mark.parametrize('rating,expected', [(None, None), ('', None), (-1, None), (0, 5), (40, 5),
    (41, 4), (60, 4), (61, 3), (80, 3), (81, 2), (100, 2), (101, 1), (130, 1)])
def test_rating_boundaries(rating, expected):
    assert directory.rating_class(rating) == expected


def test_stable_identity_and_count_are_verified():
    trainer = {'id': 'HDA', 'name': '賀賢'}
    html = '<div class="subheader">賀賢 馬匹總數 : 1</div><table><tr><td><a href="/zh-hk/local/information/horse?horseid=HK_2023_J463">禾道威 (J463)</a></td><td>(40)</td></tr></table>'
    rows = directory.parse_stable(html, trainer)
    assert rows[0]['rating'] == 40 and rows[0]['trainer']['id'] == 'HDA'
    with pytest.raises(ValueError, match='练马师'):
        directory.parse_stable(html, {'name': '另一人'})
    with pytest.raises(ValueError, match='总数'):
        directory.parse_stable(html.replace('總數 : 1', '總數 : 2'), trainer)


def test_dividend_rowspans_keep_pool_identity():
    soup = BeautifulSoup('<div class="dividend_tab"><div class="position_left"><table><tbody>'
        '<tr><td>獨贏</td><td>12</td><td>347.00</td></tr>'
        '<tr><td rowspan="2">位置</td><td>12</td><td>73.50</td></tr>'
        '<tr><td>2</td><td>13.50</td></tr>'
        '<tr><td>連贏</td><td>2,12</td><td>367.50</td></tr>'
        '<tr><td>位置Q</td><td>2,8</td><td>55</td></tr></tbody></table></div></div>', 'html.parser')
    result = racing.parse_dividends(soup)
    assert [(p['type'], p['amount']) for p in result] == [('WIN', 347), ('PLA', 73.5), ('PLA', 13.5), ('QIN', 367.5)]
    assert all(p['unit'] == 10 for p in result)


def test_cancelled_race_is_a_real_outcome_not_a_missing_result():
    html = '<div>賽事日期: 14/11/2026 沙田</div><p>此場賽事宣佈取消。單場彩池退款。</p>'
    ident = '2026-11-14-ST-6'
    value, links = racing.parse_race(html, racing.race_url(ident, True), True, ident)
    assert value['status'] == 'cancelled' and value['cancellationOfficial']
    assert value['entries'] == [] and not value['resultOfficial']
    assert [d['display'] for d in value['dividends']] == ['退款'] * 3
    with pytest.raises(ValueError, match='取消场次'):
        racing.parse_race(html, racing.race_url(ident, True), True, '2026-11-14-ST-7')


def test_missing_pool_keeps_actual_quote_time_and_first_observation():
    pool = {'oddsType': 'QIN', 'oddsLastUpdateTime': '2026-11-17T10:00:00Z',
            'oddsNodes': [{'combString': '12,2', 'oddsValue': '20', 'hotFavourite': False}]}
    first = live.merge_pool({}, pool, 'first-check')
    pool['oddsNodes'][0]['oddsValue'] = '16'
    second = live.merge_pool(first, pool, 'second-check')
    assert second['quotes'][0] == {'combination': '2,12', 'value': '16', 'first': '20',
                                  'firstAt': 'first-check', 'previous': '20', 'favourite': False}
    missing = live.merge_pool(second, {**pool, 'oddsNodes': [], 'oddsLastUpdateTime': 'later'}, 'third-check')
    assert missing['quoteRetained'] and missing['sourceUpdatedAt'] == pool['oddsLastUpdateTime']
    assert missing['quotes'] == second['quotes']


def meeting():
    return {'id': '2026-11-18-HV', 'date': '2026-11-18', 'venueCode': 'HV'}


def raw_race():
    return {'no': 1, 'status': 'RESULT', 'runners': [
        {'no': 1, 'name_ch': '禾道威', 'horse': {'id': 'HK_2023_J463', 'code': 'J463'},
         'jockey': {'code': 'PZ', 'name_ch': '潘頓'}, 'trainer': {'code': 'HDA', 'name_ch': '賀賢'}, 'finalPosition': 1},
        {'no': 15, 'status': 'STANDBY', 'horse': {'id': 'HK_2024_K500', 'code': 'K500'}}]}


def test_initial_placing_is_provisional_until_dividend_or_formal_result():
    value = live.normalize_race(meeting(), raw_race(), {})
    assert len(value['entries']) == 1 and value['status'] == 'provisional'
    assert value['entries'][0]['jockey']['id'] == 'PZ'
    official = live.normalize_race(meeting(), raw_race(), {**value, 'resultOfficial': True})
    assert official['status'] == 'finished'
    with pytest.raises(ValueError, match='身份'):
        live.normalize_race(meeting(), raw_race(), {'id': '2026-11-14-ST-1'})


def test_wrong_meeting_odds_cannot_be_published(monkeypatch):
    def query(name, variables):
        if name == 'meetings':
            return {'raceMeetings': [{**meeting(), 'races': [raw_race()]}]}
        return {'raceMeetings': [{'pmPools': [{'id': '2026-11-14-ST-WIN'}]}]}
    monkeypatch.setattr(live, 'query', query)
    monkeypatch.setattr(live, 'publish', lambda *args: pytest.fail('wrong meeting published'))
    with pytest.raises(ValueError, match='赛马日'):
        live.sync_live_racing()


def test_rankings_use_all_venue_row_once_and_keep_visitors_separate():
    def person(code, wins, visiting=False):
        return {'code': code, 'name_ch': code, 'name_en': code, 'status': 'Active', 'visitingIndex': visiting,
                'ssnStat': [{'ven': 'ST', 'numFirst': 100, 'numStarts': 110},
                            {'ven': 'ALL', 'numFirst': wins, 'numStarts': 20}], 'dhStat': []}
    rows = people.ranking_rows([person('B', 4), person('A', 8), person('VISITOR', 10, True)])
    assert [(r['id'], r['numFirst'], r['rank']) for r in rows] == [('A', 8, 1), ('B', 4, 2), ('VISITOR', 10, None)]


def test_chinese_news_rejects_foreign_hosts_future_dates_and_unrelated_sport():
    yesterday = format_datetime(datetime.now(timezone.utc) - timedelta(days=1))
    tomorrow = format_datetime(datetime.now(timezone.utc) + timedelta(days=1))
    def item(title, host='news.rthk.hk', date=yesterday):
        return f'<item><title>{title}</title><link>http://{host}/a</link><pubDate>{date}</pubDate></item>'
    xml = '<rss><channel>' + item('英超賽事新聞') + item('English only') + item('足球新聞', 'evil.example') + item('足球預告', date=tomorrow) + item('網球冠軍') + '</channel></rss>'
    rows = news.parse_feed(xml, 'football', '香港电台', 'news.rthk.hk')
    assert len(rows) == 1 and rows[0]['titleZh'] == '英超賽事新聞'
    assert rows[0]['url'].startswith('https://news.rthk.hk/')


def test_feed_failure_retains_previous_articles(tmp_path, monkeypatch):
    monkeypatch.setattr(news, 'PUBLIC', tmp_path)
    old = {'categories': {key: {'articles': [{'url': 'https://example.test/'+key, 'publishedAt': '2026-01-01', 'titleZh': '中文'}]}
                          for key in news.FEEDS}}
    monkeypatch.setattr(news, 'load', lambda path: old if path.name == 'portal-news.json' else {})
    monkeypatch.setattr(news, 'fetch_text', lambda url: (_ for _ in ()).throw(OSError('offline')))
    saved = []
    monkeypatch.setattr(news, 'publish', lambda path, value: saved.append(value))
    assert news.sync_portal_news() == 3
    assert set(saved[0]['failed']) == set(news.FEEDS)
    assert all(not category['ok'] for category in saved[0]['categories'].values())


def test_news_images_only_use_publisher_article_photos():
    assert news.news_image('<meta property="og:image" content="https://newsstatic.rthk.hk/images/mfile_123_1_M.jpg">', 'https://news.rthk.hk/a') == 'https://newsstatic.rthk.hk/images/mfile_123_1_M.jpg'
    assert news.news_image('<img src="//res.hkjc.com/racingnews/wp-content/uploads/2026/11/horse.jpg">', 'https://racingnews.hkjc.com/a') == 'https://res.hkjc.com/racingnews/wp-content/uploads/2026/11/horse.jpg'
    assert news.news_image('<img src="https://evil.example/a.jpg"><img src="https://newsstatic.rthk.hk/logo.png">', 'https://news.rthk.hk/a') is None
