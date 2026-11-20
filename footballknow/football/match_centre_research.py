"""Share daily research by verified event identity with the full match catalogue."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from .daily_scores import identities, parse_event, preserve_pregame_quotes
from .files import PUBLIC, STATE
from .leagues import league_config
from .match_details import canonical, match_catalogue, resolve_event
from .match_research import BASE, cached_json, game_of, load, research_row
from .motivation import attach_research, dt, review_match, verify_original
from .sync_control import read_control


def same_fixture(row, match, league):
    if row.get('league') != league or not dt(row.get('kickoff')):
        return False
    if match.get('kickoff'):
        if dt(row['kickoff']) != dt(match['kickoff']):
            return False
    elif dt(row['kickoff']).date().isoformat() != match['date']:
        return False
    if match['id'].startswith('espn:') and row.get('id') != match['id'].split(':')[1]:
        return False
    return all(canonical(row.get('teams', {}).get(s, {}).get('name', ''), league) ==
               canonical(match[s], league) for s in ('home', 'away'))


def summary_row(raw, match, league, stamp, names):
    header = deepcopy(raw.get('header', {}))
    event_id = str(header.get('id', ''))
    game = game_of(raw, event_id)
    header['date'] = game['date']
    header['competitions'][0]['venue'] = raw.get('gameInfo', {}).get('venue', {})
    for competitor in header['competitions'][0]['competitors']:
        side = competitor['homeAway']
        if canonical(competitor['team']['displayName'], league) != canonical(match[side], league):
            raise ValueError('Opponent identity mismatch')
        code = str(competitor['team']['id'])
        stats = next((r.get('statistics', []) for r in raw.get('boxscore', {}).get('teams', [])
                      if str(r.get('team', {}).get('id')) == code), [])
        competitor['statistics'] = stats
    row = parse_event(header, match['date'], stamp, names)
    if not same_fixture(row, match, league):
        raise ValueError('Competition or kickoff mismatch')
    return row


def get_research(match_id, league, include_detail=False):
    catalogue, matches = match_catalogue(league)
    match = next((m for m in matches if m['id'] == match_id), None)
    if not match or match.get('competition') != league_config(league).competition:
        raise LookupError('这场比赛未收录于当前赛事')
    at = datetime.now(timezone.utc)
    enabled = read_control()['enabled']
    candidates = [r for r in load(PUBLIC / 'daily-football.json').get('matches', []) if same_fixture(r, match, league)]
    row = deepcopy(candidates[0]) if len(candidates) == 1 else None
    result = {'league': league, 'matchId': match['id'], 'home': match['home'], 'away': match['away'],
              'date': match['date'], 'kickoff': match.get('kickoff'), 'paused': not enabled}
    names, contexts = identities()
    try:
        if not row or enabled and (not dt(row.get('updatedAt')) or at - dt(row['updatedAt']) > timedelta(minutes=3)):
            event_id = resolve_event(match, league, fetch_missing=enabled)
            if event_id:
                path = STATE / 'match-summaries' / (event_id + '.json')
                raw = (cached_json(f'{BASE}/summary?event={event_id}', path, 120, at) if enabled
                       else load(path).get('raw', {}))
                if raw:
                    stamp = load(path).get('updatedAt')
                    fresh_row = summary_row(raw, match, league, stamp, names)
                    row = preserve_pregame_quotes(fresh_row, row or {})
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        result['message'] = '本场部分来源暂未更新，显示可核对的已存资料。'
    if not row:
        return {**result, 'message': '同步已暂停，本场暂未保存分析资料。' if not enabled else '暂未找到可核对的本场分析资料，请稍后重新读取。'}
    if enabled:
        attach_research(row, [], contexts, at, STATE / 'daily-motivation')
    else:
        original = load(STATE / 'daily-motivation' / (row['id'] + '.json'))
        row['motivation'] = {'original': original if verify_original(original, row) else None,
                             'review': review_match(row, original)}
    cutoff = min(at, dt(row['kickoff']))
    club_ids = {str(t['id']) for t in catalogue.get('teams', []) if t['name'] in {match['home'], match['away']}}
    row['relatedNews'] = [n for n in contexts.get(league, {}).get('news', {}).get('articles', [])
                          if club_ids.intersection(str(i) for i in n.get('teamIds', [])) and dt(n.get('publishedAt'))
                          and cutoff - timedelta(days=7) <= dt(n['publishedAt']) < cutoff][:6]
    result['match'] = row
    if include_detail:
        result['supplement'] = research_row(row)
    return result
