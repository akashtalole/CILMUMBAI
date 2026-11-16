"""Polite fetching of public documents (SPEC-001/R6, R7)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

# A generic client name: no personal or project-member details (see the platform's privacy rules).
USER_AGENT = "AamchaHishob-archiver/0.1 (public civic records project)"
MAX_BYTES = 200 * 1024 * 1024


@dataclass(frozen=True)
class FetchResult:
    url: str
    final_url: str
    data: bytes
    content_type: str | None


@dataclass(frozen=True)
class FetchFailure:
    url: str
    reason: str  # http_<status>, network_error, unsupported_url, too_large, empty, not_a_document
    detail: str = ""


class Fetcher:
    """Fetches one URL at a time, waiting at least `delay_s` between requests to the same host."""

    def __init__(
        self,
        delay_s: float = 5.0,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.delay_s = delay_s
        self.client = httpx.Client(
            headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=60.0, transport=transport
        )
        self.clock = clock
        self.sleep = sleep
        self._last_request: dict[str, float] = {}

    def fetch(self, url: str) -> FetchResult | FetchFailure:
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            return FetchFailure(url, "unsupported_url", "only http and https URLs are fetched")
        host = parts.hostname
        if host in self._last_request:
            wait = self._last_request[host] + self.delay_s - self.clock()
            if wait > 0:
                self.sleep(wait)
        self._last_request[host] = self.clock()
        try:
            with self.client.stream("GET", url) as response:
                if response.status_code >= 400:
                    return FetchFailure(url, f"http_{response.status_code}", response.reason_phrase)
                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_BYTES:
                        return FetchFailure(url, "too_large", f"over {MAX_BYTES} bytes")
                    chunks.append(chunk)
                data = b"".join(chunks)
                content_type = response.headers.get("content-type")
                final_url = str(response.url)
        except httpx.HTTPError as error:
            return FetchFailure(url, "network_error", type(error).__name__)
        if not data:
            return FetchFailure(url, "empty", "the response had no body")
        return FetchResult(url, final_url, data, content_type)
