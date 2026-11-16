from football.changelog import diff_live, merge_log, LIMIT
from football.odds_history import append_history, PER_MATCH


def row(mid, **extra):
    return {'id': mid, 'home': 'A', 'away': 'B', 'kickoff': '2026-11-21T12:30:00+00:00', 'started': False, 'finished': False,
            'homeGoals': None, 'awayGoals': None, **extra}


def kinds(before, after):
    return [(e['kind'], e['from'], e['to']) for e in diff_live({'matches': before}, {'matches': after}, 'epl', 'T')]


def test_each_kind_of_change_is_recorded_once():
    assert kinds([row('1')], [row('1')]) == []
    assert kinds([row('1')], [row('1', kickoff='2026-11-22T15:00:00+00:00')]) == [('kickoff', '2026-11-21T12:30:00+00:00', '2026-11-22T15:00:00+00:00')]
    assert kinds([row('1')], [row('1', started=True, homeGoals=0, awayGoals=0)]) == [('start', None, '0:0')]
    live = row('1', started=True, homeGoals=0, awayGoals=0)
    assert kinds([live], [row('1', started=True, homeGoals=1, awayGoals=0)]) == [('score', '0:0', '1:0')]
    assert kinds([live], [row('1', started=True, finished=True, homeGoals=0, awayGoals=0)]) == [('final', '0:0', '0:0')]
    done = row('1', started=True, finished=True, homeGoals=2, awayGoals=1)
    assert kinds([done], [row('1', started=True, finished=True, homeGoals=2, awayGoals=2)]) == [('correction', '2:1', '2:2')]
    assert kinds([], [row('9')]) == [] and diff_live(None, None, 'epl', 'T') == []


def test_log_keeps_newest_first_and_is_bounded():
    log = merge_log({'entries': [{'n': i} for i in range(LIMIT)]}, [{'n': 'new'}], 'T')
    assert log['entries'][0] == {'n': 'new'} and len(log['entries']) == LIMIT


def test_opening_and_closing_quotes_are_independent_series():
    quotes = [{'provider': 'Book', 'market': '90-minute-1x2', 'phase': phase, 'via': 'Feed', 'H': price, 'D': 3.4, 'A': 4.0}
              for phase, price in [('收盘', 1.9), ('赛前', 2.1)]]
    history = append_history({}, {'m': quotes}, 't1', {'m'})
    history = append_history(history, {'m': quotes}, 't2', {'m'})
    assert len(history['m']) == 2
    quotes[0]['H'] = 1.8
    history = append_history(history, {'m': quotes}, 't3', {'m'})
    assert [(r['phase'], r['at']) for r in history['m']] == [('收盘', 't1'), ('赛前', 't1'), ('收盘', 't3')]


def test_trimming_preserves_each_provider_opening_price():
    rows = [{'at': str(i), 'provider': str(i % 2), 'H': 2 + i / 100, 'D': 3.4, 'A': 4} for i in range(PER_MATCH + 20)]
    result = append_history({'m': rows}, {}, 'now', {'m'})['m']
    assert len(result) == PER_MATCH
    assert [r['at'] for r in result[:2]] == ['0', '1']
    assert result[-1]['at'] == str(PER_MATCH + 19)


def test_price_history_adds_an_entry_only_when_a_provider_moves():
    quote = lambda h: [{'provider': 'X', 'market': '90-minute-1x2', 'H': h, 'D': 3.4, 'A': 4.0}]
    history = append_history({}, {'m': quote(2.0)}, 't1', {'m'})
    history = append_history(history, {'m': quote(2.0)}, 't2', {'m'})
    history = append_history(history, {'m': quote(1.9)}, 't3', {'m', 'empty'})
    assert [(r['at'], r['H']) for r in history['m']] == [('t1', 2.0), ('t3', 1.9)] and 'empty' not in history
    assert append_history(history, {}, 't4', set()) == {}
    assert append_history({}, {'m': [{'provider': 'X', 'market': 'other', 'H': 2, 'D': 3, 'A': 4}, {'provider': 'Y', 'market': '90-minute-1x2', 'H': None, 'D': 3, 'A': 4}]}, 't', {'m'}) == {}
    long = {'m': [{'at': str(i), 'provider': 'X', 'H': i, 'D': 3, 'A': 4} for i in range(PER_MATCH)]}
    trimmed = append_history(long, {'m': quote(999)}, 'end', {'m'})['m']
    assert len(trimmed) == PER_MATCH and trimmed[0]['at'] == '0' and trimmed[-1]['at'] == 'end'
