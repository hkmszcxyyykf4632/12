"""Price movement, keeping each provider, quote phase and source separate."""
import math

PER_MATCH = 150


def series_key(quote):
    return quote['provider'], quote.get('phase') or '采集快照', quote.get('via') or ''


def append_history(history, quotes, stamp, tracked):
    """history: {matchId: [entry]}; quotes: {matchId: [quote]}; tracked: ids worth keeping."""
    result = {key: rows for key, rows in (history or {}).items() if key in tracked}
    for match_id in tracked:
        rows = result.setdefault(match_id, [])
        for quote in quotes.get(match_id, []):
            if quote.get('market') != '90-minute-1x2' or not all(isinstance(quote.get(k), (int, float)) and math.isfinite(quote[k]) and 1 < quote[k] <= 10000 for k in 'HDA'):
                continue
            last = next((r for r in reversed(rows) if series_key(r) == series_key(quote)), None)
            prices = {k: quote[k] for k in 'HDA'}
            if not last or any(last[k] != prices[k] for k in 'HDA'):
                rows.append({'at': stamp, 'provider': quote['provider'], 'phase': quote.get('phase') or '采集快照',
                             'via': quote.get('via') or '', **prices})
        if len(rows) > PER_MATCH:
            first = {}
            for index, row in enumerate(rows):
                first.setdefault(series_key(row), index)
            keep = set(list(first.values())[-PER_MATCH:])
            for index in range(len(rows) - 1, -1, -1):
                if len(keep) >= PER_MATCH:
                    break
                keep.add(index)
            rows[:] = [row for index, row in enumerate(rows) if index in keep]
        if not rows:
            del result[match_id]
    return result
