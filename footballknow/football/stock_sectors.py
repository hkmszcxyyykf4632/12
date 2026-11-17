"""Company industries grouped for browsing, independent of exchange listing categories."""
import json
import re
import urllib.parse

from .finance import EASTMONEY, now, request


SECTORS = {
    '地产': '地产', '银行': '金融', '保险': '金融', '其他金融': '金融',
    '软件服务': '科技', '半导体': '科技', '资讯科技器材': '科技',
    '药品及生物科技': '医疗保健', '其他医疗保健': '医疗保健',
    '家庭电器及用品': '消费', '消费者主要零售商': '消费', '汽车': '消费',
    '食物饮品': '消费', '专业零售': '消费', '纺织及服饰': '消费',
    '工业工程': '工业制造', '工用支援': '工业制造',
    '煤炭': '能源资源', '原材料': '能源资源', '一般金属及矿石': '能源资源',
    '黄金及贵金属': '能源资源', '石油及天然气': '能源资源',
    '公用事业': '电讯公用', '电讯': '电讯公用',
    '旅游及消闲设施': '旅游酒店', '媒体及娱乐': '传媒娱乐',
    '建筑': '建筑工程', '支援服务': '商业服务', '工用运输': '交通运输',
}
ROW_FIELDS = ('sector', 'industry', 'industryUpdatedAt')
META_FIELDS = ('industrySource', 'industrySourceLabel', 'industryUpdatedAt', 'industryCoverage')


def classify(industry, business=''):
    industry = (industry or '').strip()
    if not industry:
        return '待分类'
    if industry == '旅游及消闲设施':
        positive = re.sub(r'(?:非|不涉及|不从事|不經營|不经营)(?:博彩|赌博|賭博|赌场|賭場|彩票)', '', business or '')
        if re.search(r'博彩|赌博|賭博|赌场|賭場|娱乐场|娛樂場|彩票', positive):
            return '博彩'
    return SECTORS.get(industry, industry)


def fetch_report(columns, filter_value=None):
    records, identities, total, pages = [], set(), None, None
    for page in range(1, 21):
        params = {'reportName': 'RPT_HKF10_INFO_ORGPROFILE', 'columns': columns,
                  'pageNumber': page, 'pageSize': 500, 'sortColumns': 'SECUCODE',
                  'sortTypes': 1, 'source': 'F10', 'client': 'PC'}
        if filter_value:
            params['filter'] = filter_value
        payload = json.loads(request(EASTMONEY + '?' + urllib.parse.urlencode(params)))
        result = payload.get('result') or {}
        count, page_count, rows = result.get('count'), result.get('pages'), result.get('data')
        if payload.get('success') is not True or not isinstance(count, int) or not isinstance(page_count, int):
            raise ValueError('Invalid industry report')
        if not 1 <= page_count <= 20 or not 0 < count <= 10000 or not isinstance(rows, list) or not rows:
            raise ValueError('Incomplete industry report')
        if total is None:
            total, pages = count, page_count
        if (count, page_count) != (total, pages):
            raise ValueError('Industry report changed during pagination')
        for row in rows:
            identity = row.get('SECUCODE')
            if not isinstance(identity, str) or identity in identities:
                raise ValueError('Duplicate or missing company identity')
            identities.add(identity)
        records.extend(rows)
        if page == pages:
            if len(records) != total:
                raise ValueError('Incomplete industry report pages')
            return records
    raise ValueError('Industry report exceeded page limit')


def enrich_catalogue(catalogue, previous=None):
    previous = previous or {}
    old = {row['code']: row for row in previous.get('stocks', [])}
    for row in catalogue['stocks']:
        saved = old.get(row['code'], {})
        if saved.get('industryUpdatedAt'):
            row.update({key: saved.get(key) for key in ROW_FIELDS})
        else:
            row['sector'] = '待分类'
    for key in META_FIELDS:
        if key in previous:
            catalogue[key] = previous[key]
    try:
        rows = fetch_report('SECUCODE,SECURITY_CODE,BELONG_INDUSTRY')
        leisure = fetch_report('SECUCODE,SECURITY_CODE,BELONG_INDUSTRY,MAIN_BUSINESS',
                               '(BELONG_INDUSTRY="旅游及消闲设施")')
        businesses = {row['SECUCODE']: row.get('MAIN_BUSINESS') or '' for row in leisure}
        industries = {row['SECURITY_CODE']: row for row in rows
                      if re.fullmatch(r'\d{5}', row.get('SECURITY_CODE') or '')
                      and row['SECUCODE'] == row['SECURITY_CODE'] + '.HK'}
        if sum(row['code'] in industries for row in catalogue['stocks']) < len(catalogue['stocks']) * .95:
            raise ValueError('Insufficient industry coverage')
        if any(row.get('BELONG_INDUSTRY') == '旅游及消闲设施' and row['SECUCODE'] not in businesses
               for row in industries.values()):
            raise ValueError('Missing leisure business profiles')
        checked = now()
        for row in catalogue['stocks']:
            profile = industries.get(row['code'], {})
            industry = (profile.get('BELONG_INDUSTRY') or '').strip()
            row.update({'industry': industry or None,
                        'sector': classify(industry, businesses.get(profile.get('SECUCODE'), '')),
                        'industryUpdatedAt': checked})
        catalogue.update({'industrySource': EASTMONEY, 'industrySourceLabel': '东方财富公司行业与业务资料',
                          'industryUpdatedAt': checked,
                          'industryCoverage': sum(row['sector'] != '待分类' for row in catalogue['stocks']),
                          'industryRefreshFailed': False})
    except (OSError, ValueError, KeyError, TypeError):
        catalogue['industryRefreshFailed'] = True
        catalogue['industryCoverage'] = sum(row.get('sector') != '待分类' for row in catalogue['stocks'])
    return catalogue
