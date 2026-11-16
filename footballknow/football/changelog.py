"""What changed between two published score snapshots, kept as a short public record."""
LIMIT = 400


def diff_live(before, after, league, stamp):
    """Entries for kickoff moves, starts, score changes, full-time and corrected results."""
    old = {m['id']: m for m in (before or {}).get('matches', [])}
    entries = []
    for m in (after or {}).get('matches', []):
        prior = old.get(m['id'])
        if not prior:
            continue
        base = {'at': stamp, 'league': league, 'matchId': m['id'], 'home': m['home'], 'away': m['away']}
        score = lambda row: None if row.get('homeGoals') is None else f"{row['homeGoals']}:{row['awayGoals']}"
        if prior.get('kickoff') != m.get('kickoff'):
            entries.append({**base, 'kind': 'kickoff', 'from': prior.get('kickoff'), 'to': m.get('kickoff')})
        if not prior.get('started') and m.get('started') and not m.get('finished'):
            entries.append({**base, 'kind': 'start', 'from': None, 'to': score(m)})
        if prior.get('finished') and m.get('finished') and score(prior) != score(m):
            # A result that changes after full time is a correction and is flagged for review.
            entries.append({**base, 'kind': 'correction', 'from': score(prior), 'to': score(m)})
        elif score(prior) != score(m) and prior.get('started') and not m.get('finished'):
            entries.append({**base, 'kind': 'score', 'from': score(prior), 'to': score(m)})
        if not prior.get('finished') and m.get('finished'):
            entries.append({**base, 'kind': 'final', 'from': score(prior), 'to': score(m)})
    return entries


def merge_log(previous, entries, stamp):
    rows = (entries + (previous or {}).get('entries', []))[:LIMIT]
    return {'version': 1, 'updatedAt': stamp, 'entries': rows}
