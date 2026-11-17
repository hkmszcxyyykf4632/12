"""Current chair biographies tied to the company's exact security identity."""
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

OFFICIAL_PORTRAITS = {
    ('00700', '马化腾'): {
        'url': 'https://www.tencent.com/wp-content/uploads/2022/12/1.jpeg',
        'source': 'https://www.tencent.com/zh-cn/team/ma-huateng-pony-ma/',
        'credit': '腾讯官方网站', 'checkedAt': '2026-11-17',
    },
}


def normalize_leaders(rows, code, chairman, fetched_at):
    today = fetched_at[:10]
    names = {s.strip() for s in re.split(r'[,，、;；/]', chairman or '') if s.strip()}
    result, seen = [], set()
    for row in rows:
        if row.get('SECUCODE') != code + '.HK':
            raise ValueError('Company leader identity mismatch')
        name = str(row.get('PERSON_NAME') or '').strip()
        role = str(row.get('POSITION_NAME') or '').strip()
        if not name or name.upper() == 'NULL':
            continue
        start, end = (row.get('INCUMBENT_START_DATE') or '')[:10], (row.get('INCUMBENT_END_DATE') or '')[:10]
        if start and start > today or end and end < today:
            continue
        chair_role = re.search(r'(?<!副)(董事会主席|董事會主席|董事局主席|董事长|董事長|联席主席|聯席主席)', role)
        if name not in names and not chair_role:
            continue
        identity = str(row.get('PERSON_CODE') or name)
        if identity in seen:
            continue
        seen.add(identity)
        resume = BeautifulSoup(str(row.get('RESUME') or ''), 'html.parser').get_text(' ', strip=True)
        sentences = [s.strip() for s in re.split(r'[。\n]+', resume) if s.strip()]
        education = [s for s in sentences if re.search(r'大学|大學|学位|學位|毕业|畢業|硕士|碩士|博士', s)]
        career = [s for s in sentences if s not in education and re.search(r'曾|任|创|創|负责|負責|加入|受雇|工作', s)]
        result.append({'name': name, 'personId': identity, 'position': role, 'startedAt': start or None,
                       'endedAt': end or None, 'degree': row.get('HIGH_DEGREE'),
                       'education': [s[:400] for s in education[:2]], 'career': [s[:400] for s in career[:4]],
                       'photo': OFFICIAL_PORTRAITS.get((code, name)), 'fetchedAt': fetched_at})
    return result


def refresh_leaders(code, chairman):
    from .finance import em_report, now
    stamp = now()
    rows = em_report(code, 'RPT_HKPCF10_BASIC_EXECUTIVEINFO', extra_filter='(NUM=1)(PERSON_NAME<>"NULL")', page_size=200)
    return {'updatedAt': stamp, 'people': normalize_leaders(rows, code, chairman, stamp),
            'source': 'https://emweb.securities.eastmoney.com/PC_HKF10/pages/home/index.html?code=' + code + '&type=web&color=w#/CompanyManager',
            'sourceLabel': '东方财富公司管理层资料',
            'scope': '按公司代码、主席姓名或正式主席职务匹配；不以行政总裁代替主席。未提供资料的字段留空。'}
