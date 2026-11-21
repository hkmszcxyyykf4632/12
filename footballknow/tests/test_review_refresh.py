import json
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

from pydantic import SecretStr

from football import football_forecasts, racing_analysis, review_refresh, reviews


def test_paused_reviews_do_not_read_models_or_candidates(monkeypatch):
    monkeypatch.setattr(review_refresh, 'read_control', lambda: {'enabled': False})
    monkeypatch.setattr(review_refresh, 'settings', lambda: (_ for _ in ()).throw(AssertionError('paused')))
    assert review_refresh.refresh() == {'paused': True, 'generated': 0}


def test_missing_model_leaves_verified_facts_visible(monkeypatch):
    monkeypatch.setattr(review_refresh, 'read_control', lambda: {'enabled': True})
    monkeypatch.setattr(review_refresh, 'settings', lambda: SimpleNamespace(apiKey=SecretStr('')))
    assert review_refresh.refresh()['generated'] == 0


def test_rescheduled_fixture_does_not_review_old_prediction(tmp_path, monkeypatch):
    monkeypatch.setattr(football_forecasts, 'STATE', tmp_path)
    monkeypatch.setattr(racing_analysis, 'STATE', tmp_path)
    row = {'id': '123', 'competitionId': '700', 'kickoff': '2026-11-21T12:00Z', 'finished': True,
           'teams': {'home': {'id': '1'}, 'away': {'id': '2'}}}
    old = {**row, 'kickoff': '2026-11-20T12:00Z'}
    with football_forecasts.connect() as db:
        db.execute('INSERT INTO forecasts VALUES (?,?,?,?,?,?)',
                   (football_forecasts.identity(old), 'initial', '123', '2026-11-20T10:00Z', json.dumps({'score': [2, 1]}), '{}'))
    monkeypatch.setattr(football_forecasts, 'current_row', lambda ident: row)
    monkeypatch.setattr(football_forecasts, 'review', lambda *args: (_ for _ in ()).throw(AssertionError('wrong fixture')))
    monkeypatch.setattr(review_refresh, 'load', lambda path: {})
    assert list(review_refresh.candidates(datetime(2026, 11, 21, 13, tzinfo=timezone.utc))) == []


def test_review_candidates_skip_out_of_scope_saved_predictions_and_editorial_cases(tmp_path, monkeypatch):
    monkeypatch.setattr(football_forecasts, 'STATE', tmp_path)
    monkeypatch.setattr(racing_analysis, 'STATE', tmp_path)
    row = {'id': '123', 'competitionId': '710', 'kickoff': '2026-11-21T12:00Z', 'finished': True,
           'teams': {'home': {'id': '1'}, 'away': {'id': '2'}}}
    with football_forecasts.connect() as db:
        db.execute('INSERT INTO forecasts VALUES (?,?,?,?,?,?)',
                   (football_forecasts.identity(row), 'initial', '123', '2026-11-21T10:00Z', json.dumps({'score': [2, 1]}), '{}'))
    monkeypatch.setattr(football_forecasts, 'current_row', lambda ident: row)
    monkeypatch.setattr(football_forecasts, 'review', lambda *args: (_ for _ in ()).throw(AssertionError('out of scope forecast')))
    monkeypatch.setattr(reviews, 'football_review', lambda *args: (_ for _ in ()).throw(AssertionError('out of scope editorial case')))
    monkeypatch.setattr(review_refresh, 'load', lambda path: {'cases': [{'identity': {'id': '123', 'league': 'ligue1'}}, {'identity': {'id': '456', 'league': 'other'}}]})
    assert list(review_refresh.candidates(datetime(2026, 11, 21, 13, tzinfo=timezone.utc))) == []


def test_editorial_review_scope_keeps_all_five_target_competitions(tmp_path, monkeypatch):
    monkeypatch.setattr(football_forecasts, 'STATE', tmp_path)
    monkeypatch.setattr(racing_analysis, 'STATE', tmp_path)
    leagues = ['epl', 'laliga', 'seriea', 'bundesliga', 'ucl']
    calls = []
    def review(ident, league, generate=False):
        calls.append((league, generate))
        return {'review': {'revision': league, 'analysisStatus': 'awaiting'}}
    monkeypatch.setattr(reviews, 'football_review', review)
    monkeypatch.setattr(review_refresh, 'load', lambda path: {'cases': [{'identity': {'id': '123', 'league': league}} for league in leagues]})
    candidates = list(review_refresh.candidates(datetime(2026, 11, 21, 13, tzinfo=timezone.utc)))
    assert [audit['revision'] for audit, action in candidates] == leagues
    for audit, action in candidates:
        action()
    assert [league for league, generate in calls if generate] == leagues
