import email.message
import io
import urllib.error

import pytest

from football import files


class Reply(io.BytesIO):
    def __init__(self, body, headers):
        super().__init__(body)
        self.headers = email.message.Message()
        for key, value in headers.items():
            self.headers[key] = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_unchanged_sources_are_revalidated_not_downloaded(tmp_path, monkeypatch):
    monkeypatch.setattr(files, 'STATE', tmp_path)
    seen = []

    def opener(request, timeout):
        seen.append(dict(request.header_items()))
        if len(seen) == 1:
            return Reply('比分 1'.encode(), {'ETag': '"v1"', 'Last-Modified': 'Mon, 16 Nov 2026 00:00:00 GMT'})
        if len(seen) == 2:
            raise urllib.error.HTTPError(request.full_url, 304, 'Not Modified', email.message.Message(), None)
        return Reply('比分 2'.encode(), {'ETag': '"v2"'})

    monkeypatch.setattr(files.urllib.request, 'urlopen', opener)
    assert files.fetch_text('https://example.test/a') == '比分 1'
    assert 'If-none-match' not in seen[0]
    assert files.fetch_text('https://example.test/a') == '比分 1'
    assert seen[1]['If-none-match'] == '"v1"' and seen[1]['If-modified-since'].startswith('Mon, 16 Nov')
    assert files.fetch_text('https://example.test/a') == '比分 2'
    assert files.fetch_text.__doc__


def test_sources_without_validators_and_real_errors_are_untouched(tmp_path, monkeypatch):
    monkeypatch.setattr(files, 'STATE', tmp_path)
    monkeypatch.setattr(files.urllib.request, 'urlopen', lambda request, timeout: Reply(b'plain', {}))
    assert files.fetch_text('https://example.test/b') == 'plain'
    assert not (tmp_path / 'http-cache').exists()

    def refuse(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 403, 'Forbidden', email.message.Message(), None)

    monkeypatch.setattr(files.urllib.request, 'urlopen', refuse)
    with pytest.raises(urllib.error.HTTPError):
        files.fetch_text('https://example.test/b')
