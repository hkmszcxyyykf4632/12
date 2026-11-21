import io
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from football.match_research import cached_json, nearing_kickoff


def test_lineup_source_uses_shared_client_and_keeps_real_source_age_on_failure():
    at = datetime(2026, 11, 21, 11, tzinfo=timezone.utc)
    raw = {'header': {'id': '401879233'}, 'rosters': []}
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'summary.json'
        def source(request, **kwargs):
            assert isinstance(request, str), 'Use the existing working ESPN client'
            return io.BytesIO(json.dumps(raw).encode())
        with patch('urllib.request.urlopen', side_effect=source):
            assert cached_json('https://site.api.espn.com/summary', path, 60, at) == raw
        with patch('football.match_research.fetch_json', side_effect=OSError('unavailable')):
            stale = cached_json('https://site.api.espn.com/summary', path, 60, at + timedelta(seconds=61))
        assert stale['_cachedSourceAt'] == at.isoformat()
        assert json.loads(path.read_text())['updatedAt'] == at.isoformat()


def test_two_hour_lineup_window_excludes_finished_and_past_matches():
    at = datetime(2026, 11, 21, 10, 30, tzinfo=timezone.utc)
    row = {'kickoff': '2026-11-21T12:30:00+00:00', 'finished': False}
    assert nearing_kickoff(row, at)
    assert not nearing_kickoff(row, at - timedelta(seconds=1))
    assert not nearing_kickoff(row, at + timedelta(hours=2, seconds=1))
    assert not nearing_kickoff({**row, 'finished': True}, at)


def test_outside_analysis_scope_does_not_fetch_research():
    from football.match_research import research_row
    with patch('football.match_research.build') as build:
        result = research_row({'id': '123', 'competitionId': '710', 'league': 'epl'})
    assert result['supported'] is False
    build.assert_not_called()
