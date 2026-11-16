import httpx

from hishob.archive.fetch import USER_AGENT, Fetcher, FetchFailure, FetchResult


class FakeTime:
    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def _fetcher(handler, delay: float = 5.0) -> tuple[Fetcher, FakeTime]:  # type: ignore[no-untyped-def]
    t = FakeTime()
    return Fetcher(delay, httpx.MockTransport(handler), clock=t.clock, sleep=t.sleep), t


def test_waits_between_requests_to_the_same_host_only() -> None:
    fetcher, t = _fetcher(lambda request: httpx.Response(200, content=b"%PDF-1.7 x"))
    fetcher.fetch("https://portal.example.gov.in/a.pdf")
    t.now += 1.0
    fetcher.fetch("https://portal.example.gov.in/b.pdf")
    fetcher.fetch("https://other.example.org/c.pdf")
    assert t.slept == [4.0]


def test_identifies_with_a_generic_client_name() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["user-agent"])
        return httpx.Response(200, content=b"%PDF-1.7")

    fetcher, _ = _fetcher(handler)
    fetcher.fetch("https://portal.example.gov.in/a.pdf")
    assert seen == [USER_AGENT]
    assert "@" not in USER_AGENT


def test_http_errors_and_bad_urls_are_failures() -> None:
    fetcher, _ = _fetcher(lambda request: httpx.Response(404))
    result = fetcher.fetch("https://portal.example.gov.in/missing.pdf")
    assert isinstance(result, FetchFailure) and result.reason == "http_404"
    bad = fetcher.fetch("ftp://portal.example.gov.in/a.pdf")
    assert isinstance(bad, FetchFailure) and bad.reason == "unsupported_url"


def test_network_errors_and_empty_bodies_are_failures() -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    fetcher, _ = _fetcher(broken)
    result = fetcher.fetch("https://portal.example.gov.in/a.pdf")
    assert isinstance(result, FetchFailure) and result.reason == "network_error"
    empty, _ = _fetcher(lambda request: httpx.Response(200, content=b""))
    assert empty.fetch("https://x.example.org/a.pdf") == FetchFailure(
        "https://x.example.org/a.pdf", "empty", "the response had no body"
    )


def test_success_returns_bytes_and_content_type() -> None:
    fetcher, _ = _fetcher(
        lambda r: httpx.Response(200, content=b"%PDF-1.7", headers={"content-type": "application/pdf"})
    )
    result = fetcher.fetch("https://portal.example.gov.in/a.pdf")
    assert isinstance(result, FetchResult)
    assert result.data == b"%PDF-1.7" and result.content_type == "application/pdf"
