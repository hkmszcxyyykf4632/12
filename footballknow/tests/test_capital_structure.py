from football.capital_structure import classify


def company(cash=100, short=20, long=30):
    return {'code': '00001', 'financials': {'statements': {'balance': [
        {'code': code, 'name': code, 'date': '2026-06-30', 'currency': '人民币', 'amount': amount}
        for code, amount in [('004002010', cash), ('004011010', short), ('004020001', long)]]}}}


def test_cash_debt_and_zero_are_distinct():
    assert classify(company())['category'] == 'cash'
    assert classify(company(10))['category'] == 'debt'
    assert classify(company(0, 0, 0))['category'] == 'balanced'


def test_missing_debt_and_mixed_currency_never_become_cash_rich():
    c = company(); c['financials']['statements']['balance'].pop()
    assert classify(c)['category'] == 'unknown'
    c = company(); c['financials']['statements']['balance'][1]['currency'] = '美元'
    assert classify(c)['category'] == 'unknown'
    assert classify(company(100, None, 30))['category'] == 'unknown'


def test_financial_firms_separate_and_latest_incomplete_not_replaced_by_old():
    c = company(); c['financials']['statements']['balance'].append({'code': '001001999', 'date': '2026-06-30'})
    assert classify(c)['category'] == 'special'
    c = company(); c['financials']['statements']['balance'].append({'code': '004002010', 'date': '2026-09-30', 'amount': 200, 'currency': '人民币'})
    assert classify(c)['category'] == 'unknown'


def test_legacy_statement_amount_currency_preserves_original_report_currency(tmp_path):
    import json
    from football.finance import load
    path = tmp_path / 'company.json'
    source = company()
    for row in source['financials']['statements']['balance']:
        row['currency'] = '港元'
    path.write_text(json.dumps(source), encoding='utf-8')
    result = load(path)
    assert result['financials']['amountCurrency'] == 'CNY'
    assert all(row['currency'] == '人民币' and row['reportCurrency'] == '港元'
               for row in result['financials']['statements']['balance'])
    assert classify(result)['category'] == 'cash'
    path.write_text(json.dumps(result), encoding='utf-8')
    assert load(path) == result
