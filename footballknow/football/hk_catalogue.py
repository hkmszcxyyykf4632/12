"""HKEX security classification is the boundary for the stock catalogue."""
import io
import re
import urllib.request
import zipfile
from datetime import datetime
from xml.etree import ElementTree as ET

from .files import publish, read_json
from .finance import FOLDER, now, request, parse_tencent
from .stock_sectors import enrich_catalogue

SOURCE = 'https://www.hkex.com.hk/eng/services/trading/securities/securitieslists/ListOfSecurities.xlsx'
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def parse_catalogue(raw, hsi, previous=None):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if sum(info.file_size for info in archive.infolist()) > 80_000_000:
            raise ValueError('Oversized securities workbook')
        strings = [''.join(item.itertext()) for item in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si', NS)]
        sheet = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
    records, source_date = [], None
    hsi_by_code = {row['code']: row for row in hsi}
    old = {row['code']: row for row in (previous or {}).get('stocks', [])}
    for row in sheet.findall('.//s:row', NS):
        cells = {}
        for cell in row.findall('s:c', NS):
            value = cell.find('s:v', NS)
            text = value.text if value is not None and value.text else ''
            cells[re.sub(r'\d', '', cell.get('r', ''))] = strings[int(text)] if cell.get('t') == 's' and text else text
        date_match = re.search(r'Updated as at (\d{2}/\d{2}/\d{4})', cells.get('A', ''))
        if date_match:
            source_date = datetime.strptime(date_match[1], '%d/%m/%Y').date().isoformat()
        category, subtype, code = cells.get('C'), cells.get('D'), cells.get('A', '')
        if category not in {'Equity', 'Real Estate Investment Trusts'}:
            continue
        if not re.fullmatch(r'\d{5}', code) or not cells.get('B') or cells.get('Q') not in {'HKD', 'CNY', 'RMB', 'USD'}:
            raise ValueError('Invalid HKEX stock identity or currency')
        known = hsi_by_code.get(code, old.get(code, {}))
        records.append({'code': code, 'name': known.get('name', cells['B']), 'englishName': cells['B'],
                        'sector': known.get('sector', '未分类'), 'isHsi': code in hsi_by_code,
                        'board': 'GEM' if subtype == 'Equity Securities (GEM)' else '主板',
                        'category': category, 'subCategory': subtype, 'currency': cells['Q'],
                        'boardLot': int(cells.get('E', '0').replace(',', '') or '0'),
                        'isin': cells.get('F'), 'rmbCounter': cells.get('R') or None})
    if not source_date or len(records) < 2000 or len({row['code'] for row in records}) != len(records):
        raise ValueError('Incomplete HKEX stock catalogue')
    return {'version': 1, 'updatedAt': now(), 'effectiveDate': source_date, 'source': SOURCE,
            'sourceLabel': '港交所完整证券名单', 'stocks': sorted(records, key=lambda row: row['code']),
            'scope': '主板、GEM、投资公司、存托凭证、交易型股票及 REIT；独立交易柜台分别列示，不含窝轮、牛熊证、ETF 或债券。'}


def refresh_catalogue():
    path = FOLDER / 'stocks.json'
    previous = read_json(path) if path.exists() else {}
    req = urllib.request.Request(SOURCE, headers={'User-Agent': 'Mozilla/5.0 FootballKnow/3.0'})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read(8_000_001)
    if len(raw) > 8_000_000:
        raise ValueError('Oversized stock catalogue response')
    result = parse_catalogue(raw, read_json(FOLDER / 'constituents.json')['constituents'], previous)
    unresolved = [row for row in result['stocks'] if not re.search(r'[\u3400-\u9fff]', row['name'])]
    for offset in range(0, len(unresolved), 40):
        batch = unresolved[offset:offset + 40]
        codes = {row['code'] for row in batch}
        try:
            quotes = parse_tencent(request('https://qt.gtimg.cn/q=' + ','.join('hk' + code for code in codes), 'gb18030'), codes, now())
            for row in batch:
                if row['code'] in quotes:
                    row['name'] = quotes[row['code']]['name']
        except (OSError, ValueError, UnicodeError):
            pass
    enrich_catalogue(result, previous)
    publish(path, result)
    return result
