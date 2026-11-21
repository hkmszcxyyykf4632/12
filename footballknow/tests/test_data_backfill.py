import json
import pytest
from football import data_backfill as bf


@pytest.fixture
def queue(tmp_path, monkeypatch):
    monkeypatch.setattr(bf, 'PUBLIC', tmp_path / 'public')
    monkeypatch.setattr(bf, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(bf, 'read_control', lambda: {'enabled': True})
    stocks = {'stocks': [{'code': f'{n:05}'} for n in range(1, 5)]}
    bf.publish(bf.PUBLIC / 'finance/stocks.json', stocks)
    def company(ident):
        value = {'code': ident, 'profile': {'legalName': ident, 'business': 'test'},
                 'holders': {'rows': [{'name': 'test'}]}, 'financials': {'amountCurrency': 'CNY',
                 'statements': {k: [{'amount': 1, 'currency': '人民币'}] for k in ['balance', 'income', 'cashflow']}}}
        bf.publish(bf.detail_path('companies', ident), value)
        return value
    monkeypatch.setattr(bf, 'refresh_company', company)
    monkeypatch.setattr('football.capital_structure.refresh_capital_index', lambda: None)
    return tmp_path


def test_whole_catalogue_advances_across_batches_and_restart(queue):
    first = bf.refresh('companies', 2)
    second = bf.refresh('companies', 2)
    assert first['total'] == 4 and first['complete'] == 2
    assert second['complete'] == 4 and second['fields']['balance'] == 4
    assert bf.refresh('companies', 2)['attemptedThisRun'] == 0


def test_partial_and_failed_sources_do_not_claim_complete_or_starve_others(queue, monkeypatch):
    def partial(ident):
        if ident == '00001': raise OSError('unavailable')
        bf.publish(bf.detail_path('companies', ident), {'code': ident, 'profile': {'legalName': ident}})
    monkeypatch.setattr(bf, 'refresh_company', partial)
    assert bf.refresh('companies', 2)['complete'] == 0
    result = bf.refresh('companies', 2)
    assert result['checked'] == 4 and result['retrying'] == 4
    assert result['fields']['profile'] == 3 and result['fields']['balance'] == 0


def test_pause_never_fetches_sources(queue, monkeypatch):
    monkeypatch.setattr(bf, 'read_control', lambda: {'enabled': False})
    monkeypatch.setattr(bf, 'refresh_company', lambda _: pytest.fail('must not fetch'))
    result = bf.refresh('companies')
    assert result['paused'] and result['attemptedThisRun'] == 0


def test_unraced_horse_is_not_falsely_missing_sectionals(queue):
    ident = 'HK_2026_J313'
    bf.publish(bf.PUBLIC / 'racing/horses' / (ident + '.json'),
               {'id': ident, 'records': [], 'profile': {'冠-亞-季-總出賽次數': '0-0-0-0'}})
    result = bf.coverage('horse-research', {'horseId': ident, 'workouts': {'fetchedAt': '2026-11-21'}})
    assert result == {'workouts': True, 'sectionals': True}


def test_empty_history_without_official_zero_starts_is_incomplete(queue):
    ident = 'HK_2026_J313'
    bf.publish(bf.PUBLIC / 'racing/horses' / (ident + '.json'), {'id': ident, 'records': []})
    assert not bf.coverage('horse-research', {'horseId': ident})['sectionals']


def test_mainland_catalogue_is_backfilled_too(queue):
    bf.publish(bf.PUBLIC / 'finance/cn-stocks.json', {'stocks': [{'code': '600519'}]})
    assert bf.refresh('companies', 10)['complete'] == 5


def test_null_financial_values_are_not_complete(queue):
    value = {'financials': {'statements': {'balance': [{'amount': None}]}}}
    assert not bf.coverage('companies', value)['balance']
