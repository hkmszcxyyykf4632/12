import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from football import ai, analysis, evaluation, history, laliga
from football.analysis import Match, MatchAnalysis, Club
from football.leagues import league_path
from football.names import Player
from football.name_rosters import roster_names, matched_roster_name
from server import app


def fixture(competition='西甲'):
    return Match(id='same-team-fixture', date='2026-12-01', kickoff='2026-12-01T20:00:00+00:00',
                 home='A', away='B', finished=False, season='2026/27', competition=competition)


def test_only_known_league_paths_and_api_parameters(tmp_path):
    assert league_path(tmp_path) == tmp_path
    assert league_path(tmp_path, 'laliga') == tmp_path / 'laliga'
    with pytest.raises(ValueError):
        league_path(tmp_path, '../private')
    assert TestClient(app).get('/api/analysis/4?league=unknown').status_code == 422


def test_poisson_and_backtest_do_not_mix_leagues():
    rows = [fixture().model_copy(update={'id': str(i), 'date': f'2026-10-{i+1:02}',
             'homeGoals': 2, 'awayGoals': 1, 'finished': True, 'season': '2025/26',
             'home': f'H{i}', 'away': f'A{i}'}) for i in range(25)]
    foreign = [r.model_copy(update={'competition': '英超', 'homeGoals': 9, 'awayGoals': 0}) for r in rows]
    assert analysis.poisson_baseline(rows, fixture()) == analysis.poisson_baseline(rows + foreign, fixture())
    final = fixture().model_copy(update={'finished': True, 'homeGoals': 1, 'awayGoals': 0})
    tested = evaluation.baseline_backtest(rows + foreign + [final], '2026/27', '西甲')
    assert tested['samples'] == 1
    assert evaluation.baseline_backtest(rows + [final], '2026/27', '英超')['samples'] == 0


def test_same_team_ids_keep_ai_reports_and_forecasts_separate(tmp_path, monkeypatch):
    monkeypatch.setattr(ai, 'STATE', tmp_path)
    monkeypatch.setattr(evaluation, 'STATE', tmp_path)
    for league, pick in [('epl', 'H'), ('laliga', 'A')]:
        folder = league_path(tmp_path, league) / 'analyses'
        folder.mkdir(parents=True)
        result = ai.AIResult(league=league, teamId=4, fixtureId='same-team-fixture',
             generatedAt='2026-11-15', snapshotAt='2026-11-15', model='test', rulesVersion='test', text=league)
        (folder / '4.json').write_text(result.model_dump_json(), encoding='utf-8')
        match = fixture('英超' if league == 'epl' else '西甲')
        report = MatchAnalysis(generatedAt='2026-11-15', dataUpdatedAt='2026-11-15', liveUpdatedAt=None,
                              team=Club(id=4, name='A', cn='甲'), match=match, checklist=[])
        assert evaluation.record_forecast(report, pick, 'test', 'v1', '2026-11-15T08:00:00+00:00', league)
        assert not evaluation.record_forecast(report, 'D', 'test', 'v2', '2026-11-15T09:00:00+00:00', league)
    assert ai.cached_analysis(4).text == 'epl'
    assert ai.cached_analysis(4, 'laliga').text == 'laliga'
    finished = fixture().model_copy(update={'finished': True, 'homeGoals': 0, 'awayGoals': 1})
    assert evaluation.prospective_results([finished], 'laliga')['correct'] == 1
    assert evaluation.prospective_results([finished])['pending'] == 1


def matchday():
    return {'season': '2026', 'gameweek': {'week': 1}, 'matches': [
        {'id': i, 'home_team': {'id': i}, 'away_team': {'id': i + 10},
         'status': 'PreMatch', 'date': '2026-12-01T00:00:00+00:00'} for i in range(1, 11)]}


def catalogue():
    return {'season': '2026/27', 'teams': [{'id': i, 'name': f'Team{i}'} for i in range(1, 21)]}


def test_official_states_do_not_invent_kickoff_or_settle_provisional_scores():
    data = matchday()
    data['matches'][0].update(status='SecondHalf', home_score=2, away_score=1, time='2026-12-01T20:00:00+00:00')
    data['matches'][1].update(status='FullTime', home_score=0, away_score=0)
    data['matches'][2].update(status='Postponed', time='2026-12-01T20:00:00+00:00')
    rows = laliga.parse_round(data, catalogue(), 'https://www.laliga.com/')
    assert rows[0]['started'] and not rows[0]['finished'] and rows[0]['result'] is None
    assert rows[1]['finished'] and rows[1]['result'] == 'D'
    assert rows[1]['scoreScope'] == '90分钟含补时'
    assert rows[2]['kickoff'] is None and rows[3]['kickoff'] is None
    data['matches'][1]['home_score'] = None
    with pytest.raises(OSError):
        laliga.parse_round(data, catalogue(), 'https://www.laliga.com/')


def test_incomplete_official_refresh_keeps_last_success(tmp_path, monkeypatch):
    folder = tmp_path / 'laliga'
    folder.mkdir()
    (folder / 'data.json').write_text(json.dumps(catalogue()))
    original = json.dumps({'version': 1, 'season': '2026/27', 'updatedAt': 'previous', 'matches': []})
    (folder / 'live.json').write_text(original)
    monkeypatch.setattr(laliga, 'PUBLIC', tmp_path)
    incomplete = matchday()
    incomplete['matches'].pop()
    monkeypatch.setattr(laliga, 'page_data', lambda _: incomplete)
    with pytest.raises(OSError):
        laliga.refresh_laliga_live()
    assert (folder / 'live.json').read_text() == original


def test_spanish_transfers_keep_real_window_without_inventing_dates(monkeypatch):
    markup = '<h2>La Liga</h2><h3>Barcelona</h3><table class="wikitable"><tr><th>Player</th></tr><tr><td>Alex (on loan from Real Betis)</td></tr><tr><td>Sam (to Celta Vigo)</td></tr></table>'
    monkeypatch.setattr(history, 'fetch_text', lambda _: markup)
    rows = history.collect_spanish_transfers('https://example.org/transfers', {'Barcelona'}, '2026 夏窗')
    assert len(rows) == 2
    assert rows[0].fromTeam == 'Betis' and rows[0].type == '租借'
    assert rows[1].toTeam == 'Celta'
    assert all(r.date == '' and r.window == '2026 夏窗' for r in rows)


def test_current_roster_navbox_names_use_full_titles_and_reject_ambiguity():
    markup = '<table class="navbox"><tr><td><span class="agent vcard"><span class="ilh-all" data-lang-code="en" data-foreign-title="Sergio Herrera Pirón"><span class="ilh-page"><a title="塞尔希奥·埃雷拉（页面不存在）">埃雷拉</a></span></span></span></td></tr></table>'
    found = roster_names(markup)
    assert found['sergioherrerapiron'] == '塞尔希奥·埃雷拉'
    player = Player(id=1, code=1, first_name='Sergio', second_name='Herrera', web_name='Sergio Herrera')
    assert matched_roster_name(player, found, found)[0] == 'sergioherrerapiron'
    ambiguous = {**found, 'sergioherreragarcia': '另一人'}
    assert matched_roster_name(player, ambiguous, ambiguous)[0] is None
