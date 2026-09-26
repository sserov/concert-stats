"""HTTP fetcher with on-disk cache, retries and error logging."""

import hashlib
import time

import httpx

USER_AGENT = "concert-stats/0.1 (personal research)"


def _cache_path(cache_dir, url):
    return cache_dir / f"{hashlib.sha1(url.encode()).hexdigest()}.body"


def fetch(
    url: str,
    cache_dir,
    client: httpx.Client | None = None,
    retries: int = 3,
    timeout: float = 30.0,
) -> str | None:
    """Fetch `url` with disk cache; return decoded body or None on final failure."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(cache_dir, url)
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")

    own_client = client is None
    if own_client:
        client = httpx.Client(
            timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}
        )
    try:
        for attempt in range(retries):
            try:
                resp = client.get(url)
                if resp.status_code >= 500:
                    raise httpx.TransportError(f"HTTP {resp.status_code}")
                if resp.status_code >= 400:
                    _log_error(cache_dir, url, f"HTTP {resp.status_code}")
                    return None
                body = resp.content.decode("utf-8", errors="replace")
                path.write_text(body, encoding="utf-8")
                time.sleep(0.3)
                return body
            except httpx.TransportError as exc:
                if attempt == retries - 1:
                    _log_error(cache_dir, url, str(exc))
                    return None
                time.sleep(2**attempt)
        return None
    finally:
        if own_client:
            client.close()


def _log_error(cache_dir, url: str, reason: str) -> None:
    with (cache_dir / "_errors.log").open("a", encoding="utf-8") as fh:
        fh.write(f"{url}\t{reason}\n")
