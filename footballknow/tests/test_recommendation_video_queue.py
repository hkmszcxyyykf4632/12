from datetime import timedelta

from football import recommendation_video_queue as queue
from football.files import publish
from test_football_forecasts import AT


def test_queue_is_idempotent_and_excludes_late_or_already_published(tmp_path, monkeypatch):
    monkeypatch.setattr(queue, 'PUBLIC', tmp_path)
    receipt = {'status': 'pending', 'home': '甲队', 'away': '乙队', 'asianSide': 'A',
               'line': -.5, 'score': [1, 1], 'scoreCandidates': [[1, 1], [0, 1]]}
    record = {'event': '123', 'domain': 'football', 'group': 'epl|2026|12', 'stage': 'initial',
              'issuedAt': AT.isoformat(), 'kickoff': (AT+timedelta(days=1)).isoformat(), 'receipt': receipt}
    first = queue.refresh_queue([record], AT)['jobs']
    assert len(first) == 1 and first[0]['dialogue'][3] == '甲队让乙队半球啊。'
    assert first[0]['dialogue'][5] == '一比一，或者零比一啊。'
    assert queue.refresh_queue([record], AT+timedelta(hours=1))['jobs'][0]['id'] == first[0]['id']
    assert not queue.refresh_queue([record], AT+timedelta(days=1))['jobs']
    publish(tmp_path/'media/recommendation-videos.json', {'videos': [{'event': '123', 'url': 'video', 'poster': 'poster'}]})
    assert not queue.refresh_queue([record], AT)['jobs']
