import copy
import json
import urllib.parse

import pytest

from football import stock_sectors as sectors


def test_business_backed_gaming_and_industry_groups():
    assert sectors.classify('银行') == '金融'
    assert sectors.classify('保险') == '金融'
    assert sectors.classify('半导体') == '科技'
    assert sectors.classify('地产') == '地产'
    assert sectors.classify('旅游及消闲设施', '经营赌场、酒店及非博彩设施') == '博彩'
    assert sectors.classify('旅游及消闲设施', '提供非博彩酒店及餐饮服务') == '旅游酒店'
    assert sectors.classify('旅游及消闲设施', '彩票设备销售') == '博彩'
    assert sectors.classify(None) == '待分类'


def test_paginated_report_requires_all_rows_and_unique_identities(monkeypatch):
    pages = [dict(success=True, result=dict(count=2, pages=2, data=[{'SECUCODE': '00001.HK'}])),
             dict(success=True, result=dict(count=2, pages=2, data=[{'SECUCODE': '00002.HK'}]))]
    def request(url):
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        return json.dumps(pages[int(query['pageNumber'][0]) - 1])
    monkeypatch.setattr(sectors, 'request', request)
    assert len(sectors.fetch_report('SECUCODE')) == 2
    pages[1]['result']['data'] = [{'SECUCODE': '00001.HK'}]
    with pytest.raises(ValueError, match='Duplicate'):
        sectors.fetch_report('SECUCODE')
    pages[1]['result']['data'] = []
    with pytest.raises(ValueError, match='Incomplete'):
        sectors.fetch_report('SECUCODE')


def test_enrichment_is_atomic_on_failure_and_does_not_guess_unknown(monkeypatch):
    rows = [{'SECUCODE': '00001.HK', 'SECURITY_CODE': '00001', 'BELONG_INDUSTRY': '银行'},
            {'SECUCODE': '00002.HK', 'SECURITY_CODE': '00002', 'BELONG_INDUSTRY': '旅游及消闲设施'},
            {'SECUCODE': '00003.HK', 'SECURITY_CODE': '00003', 'BELONG_INDUSTRY': None}]
    business = [{**rows[1], 'MAIN_BUSINESS': '在澳门经营博彩及酒店业务'}]
    monkeypatch.setattr(sectors, 'fetch_report', lambda columns, filter_value=None: business if filter_value else rows)
    current = {'stocks': [{'code': code} for code in ['00001', '00002', '00003']]}
    sectors.enrich_catalogue(current)
    assert [row['sector'] for row in current['stocks']] == ['金融', '博彩', '待分类']
    assert current['industryCoverage'] == 2
    old = copy.deepcopy(current)
    monkeypatch.setattr(sectors, 'fetch_report', lambda *args: (_ for _ in ()).throw(OSError('offline')))
    failed = {'stocks': [{'code': '00001', 'name': 'new name'}, {'code': '00004'}]}
    sectors.enrich_catalogue(failed, old)
    assert failed['industryRefreshFailed'] is True
    assert failed['industryUpdatedAt'] == old['industryUpdatedAt']
    assert failed['industryCoverage'] == 1
    assert failed['stocks'][0]['sector'] == '金融'
    assert failed['stocks'][0]['name'] == 'new name'
    assert failed['stocks'][1]['sector'] == '待分类'


def test_wrong_exchange_or_missing_gaming_profiles_cannot_replace_good_data(monkeypatch):
    old = {'stocks': [{'code': '00001', 'sector': '博彩', 'industry': '旅游及消闲设施', 'industryUpdatedAt': '2026-11-16'}]}
    for identity in ['00001.SH', '00001.HK']:
        rows = [{'SECUCODE': identity, 'SECURITY_CODE': '00001', 'BELONG_INDUSTRY': '旅游及消闲设施'}]
        monkeypatch.setattr(sectors, 'fetch_report', lambda columns, filter_value=None: [] if filter_value else rows)
        value = sectors.enrich_catalogue({'stocks': [{'code': '00001'}]}, old)
        assert value['industryRefreshFailed'] is True
        assert value['stocks'][0]['sector'] == '博彩'
