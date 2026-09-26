import httpx

from concert_stats.fetcher import fetch


def _client_with(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_returns_body_and_populates_cache(tmp_path):
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(200, text="<html>hi</html>")

    body = fetch("https://example.com/a", tmp_path, client=_client_with(handler))
    assert body == "<html>hi</html>"
    assert any(f.name.endswith(".body") for f in tmp_path.iterdir())


def test_fetch_uses_cache_no_second_request(tmp_path):
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(200, text="<html>hi</html>")

    client = _client_with(handler)
    fetch("https://example.com/a", tmp_path, client=client)
    fetch("https://example.com/a", tmp_path, client=client)
    assert len(calls) == 1


def test_fetch_retries_on_5xx_then_succeeds(tmp_path):
    attempts = []

    def handler(request):
        attempts.append(1)
        if len(attempts) < 3:
            return httpx.Response(500)
        return httpx.Response(200, text="ok")

    body = fetch("https://example.com/flaky", tmp_path, client=_client_with(handler))
    assert body == "ok"
    assert len(attempts) == 3


def test_fetch_no_retry_on_404(tmp_path):
    attempts = []

    def handler(request):
        attempts.append(1)
        return httpx.Response(404)

    assert fetch("https://example.com/gone", tmp_path, client=_client_with(handler)) is None
    assert len(attempts) == 1
    log = (tmp_path / "_errors.log").read_text()
    assert "https://example.com/gone" in log


def test_fetch_decodes_invalid_utf8(tmp_path):
    def handler(request):
        return httpx.Response(200, content=b"<html>\x98 caf\xc3\xa9</html>")

    body = fetch("https://example.com/bin", tmp_path, client=_client_with(handler))
    assert body is not None and "café" in body
