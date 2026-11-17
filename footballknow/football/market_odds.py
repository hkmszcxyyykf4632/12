"""Separate markets and phases; never infer an opening price from first observation."""
import math
import re


def line_value(value):
    if value is None or isinstance(value, bool) or str(value).strip() == '':
        return None
    try:
        n = float(re.sub(r'^[ou]', '', str(value)))
        return n if math.isfinite(n) and abs(n) <= 30 and n * 4 == round(n * 4) else None
    except ValueError:
        return None


def historical_markets(row, source, stamp):
    from .odds import decimal, PROVIDERS
    result = []
    for code, (provider, official) in {'Avg': ('市场平均', ''), **PROVIDERS}.items():
        for suffix, phase in [('', 'preclosing'), ('C', 'closing')]:
            base = {'provider': provider, 'phase': phase, 'via': 'Football-Data', 'source': source,
                    'officialUrl': official, 'fetchedAt': stamp, 'quotedAt': None,
                    'kind': 'aggregate' if code == 'Avg' else 'exchange' if code == 'BFE' else 'bookmaker'}
            markets = [
                ('90-minute-1x2', None, {s: decimal(row.get(code + suffix + s)) for s in ('H', 'D', 'A')}),
                ('total-goals', 2.5, {s: decimal(row.get(code + suffix + sign + '2.5')) for s, sign in [('O', '>'), ('U', '<')]}),
                ('asian-handicap', line_value(row.get('AHCh' if suffix else 'AHh')),
                 {s: decimal(row.get(code + suffix + 'AH' + s)) for s in ('H', 'A')}),
            ]
            for market, line, prices in markets:
                if all(prices.values()) and (market == '90-minute-1x2' or line is not None):
                    result.append({**base, 'market': market, 'line': line, 'prices': prices})
    return result


def espn_markets(raw, event_id, stamp):
    from .odds import american
    game = raw.get('header', {}).get('competitions', [{}])[0]
    if str(raw.get('header', {}).get('id')) != str(event_id):
        return []
    sides = {c['homeAway']: str(c['id']) for c in game.get('competitors', [])}
    if set(sides) != {'home', 'away'}:
        return []
    completed = game.get('status', {}).get('type', {}).get('completed') is True
    result = []
    for quote in raw.get('odds', []) or raw.get('pickcenter', []):
        provider = quote.get('provider', {}).get('name')
        if not provider or any(str(quote.get(k + 'TeamOdds', {}).get('team', {}).get('id', '')) != sides[k] for k in sides):
            continue
        base = {'provider': provider, 'via': 'ESPN', 'fetchedAt': stamp, 'quotedAt': None, 'kind': 'bookmaker',
                'source': f'https://www.espn.com/soccer/odds/_/gameId/{event_id}'}
        for source_phase, phase in [('open', 'opening'), ('close', 'closing' if completed else 'latest')]:
            for field, market, keys in [('moneyline', '90-minute-1x2', {'H': 'home', 'D': 'draw', 'A': 'away'}),
                                         ('pointSpread', 'asian-handicap', {'H': 'home', 'A': 'away'}),
                                         ('total', 'total-goals', {'O': 'over', 'U': 'under'})]:
                values = {key: quote.get(field, {}).get(side, {}).get(source_phase, {}) for key, side in keys.items()}
                prices = {key: american(value.get('odds')) for key, value in values.items()}
                line = None
                if market == 'asian-handicap':
                    line, away = line_value(values['H'].get('line')), line_value(values['A'].get('line'))
                    if line is None or away is None or line != -away:
                        continue
                elif market == 'total-goals':
                    line = line_value(values['O'].get('line'))
                    if line is None or line < 0 or line != line_value(values['U'].get('line')):
                        continue
                if all(prices.values()):
                    result.append({**base, 'market': market, 'phase': phase, 'line': line,
                                   'prices': {k: round(v, 4) for k, v in prices.items()}})
    return result


def combine_quotes(existing, incoming):
    keys = lambda q: (q['provider'], q['market'], q['phase'], q['via'], q.get('line'))
    replaced = {(q['provider'], q['market'], q['phase'], q['via']) for q in incoming}
    result = {keys(q): q for q in existing if (q['provider'], q['market'], q['phase'], q['via']) not in replaced}
    result.update({keys(q): q for q in incoming})
    return list(result.values())


def append_market_history(previous, quotes, tracked, stamp):
    result = {key: value for key, value in previous.items() if key in tracked}
    for match_id in tracked:
        rows = [q for q in quotes.get(match_id, []) if q['phase'] == 'latest']
        history = list(result.get(match_id, []))
        for row in rows:
            key = (row['provider'], row['market'], row['via'])
            last = next((q for q in reversed(history) if (q['provider'], q['market'], q['via']) == key), None)
            if last is None or last.get('line') != row.get('line') or last['prices'] != row['prices']:
                history.append({**row, 'observedAt': stamp})
        if history:
            result[match_id] = history[-500:]
    return result
