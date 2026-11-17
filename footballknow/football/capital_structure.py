"""Compare disclosed cash/deposits with borrowings, bonds and lease liabilities."""
import math
import threading
from datetime import datetime, timezone

from .files import publish
from .finance import FOLDER, load, now

LOCK = threading.Lock()
CASH = {'004002010', '004002011', '004001030'}
DEBT = {'004011010', '004020001', '004020007', '004020018', '004011006', '004020005'}
METHOD = '现金多：已披露现金及等价物、短期与中长期存款之和大于已披露借款、债券及租赁负债；负债多则相反。这是统一报表字段比较，不等同公司自行定义的净现金；不含受限制现金与证券投资。银行、保险及非普通报表单列。'


def classify(company):
    finance = company.get('financials', {})
    rows = finance.get('statements', {}).get('balance', [])
    today = datetime.now(timezone.utc).date().isoformat()
    dates = sorted({r.get('date', '') for r in rows if r.get('date') and r['date'] <= today})
    result = {'code': company.get('code'), 'category': 'unknown', 'label': '待补资料', 'reportDate': dates[-1] if dates else None,
              'source': company.get('source'), 'sourceLabel': company.get('sourceLabel'), 'updatedAt': now(), 'cash': None, 'debt': None, 'net': None}
    if not dates:
        return result
    period = [r for r in rows if r.get('date') == dates[-1]]
    if any(str(r.get('code', '')).startswith(('001', '002', '003')) for r in period):
        return {**result, 'category': 'special', 'label': '金融业独立口径'}
    by_code = {str(r.get('code')): r for r in period}
    # Require the cash anchor and both maturity buckets; omitted rows are not zero.
    required = {'004002010', '004011010', '004020001'}
    relevant = [r for r in period if str(r.get('code')) in CASH | DEBT]
    if not required <= by_code.keys() or any(not isinstance(r.get('amount'), (int, float)) or not math.isfinite(r['amount']) or r['amount'] < 0 for r in relevant):
        return result
    currencies = {r.get('currency') for r in relevant}
    if len(currencies) != 1 or None in currencies:
        return result
    cash = sum(r['amount'] for r in relevant if str(r.get('code')) in CASH)
    debt = sum(r['amount'] for r in relevant if str(r.get('code')) in DEBT)
    net = cash - debt
    category = 'cash' if net > .01 else 'debt' if net < -.01 else 'balanced'
    return {**result, 'category': category, 'label': {'cash': '现金多', 'debt': '负债多', 'balanced': '现金负债相当'}[category],
            'cash': cash, 'debt': debt, 'net': net, 'currency': next(iter(currencies)),
            'components': [{'name': r['name'], 'code': r['code'], 'amount': r['amount'], 'group': 'cash' if str(r['code']) in CASH else 'debt'} for r in relevant]}


def refresh_capital_index():
    with LOCK:
        rows = {}
        for path in (FOLDER / 'companies').glob('*.json'):
            company = load(path)
            if company.get('code') == path.stem:
                rows[path.stem] = classify(company)
        result = {'updatedAt': now(), 'rows': rows, 'method': METHOD}
        publish(FOLDER / 'capital-structure.json', result)
        return result


def update_capital_index(company):
    with LOCK:
        result = load(FOLDER / 'capital-structure.json')
        rows = result.get('rows', {})
        rows[company['code']] = classify(company)
        publish(FOLDER / 'capital-structure.json', {'updatedAt': now(), 'rows': rows, 'method': METHOD})
