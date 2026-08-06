"""Unit tests for the HTML fetcher/parser (RAG ingestion)."""
import httpx
import pytest

from app.rag.fetcher import Page, _clean_text, fetch_page, validate_url

FIXTURE_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>   Product Docs — Acme  </title>
  <meta property="og:title" content="Acme Product Docs">
</head>
<body>
  <nav>
    <a href="/pricing">Pricing</a>
    <a href="/about">About</a>
  </nav>
  <header>Site header banner</header>
  <script>var secret = "should not appear";</script>
  <style>.css{color:red}</style>
  <main>
    <h1>Welcome to Acme</h1>
    <p>Acme sells    widgets   at scale.</p>
    <p>Trusted by thousands of teams.</p>
  </main>
  <footer>Copyright 2025 Acme</footer>
</body>
</html>
"""


class _FakeClient:
    """Minimal httpx.Client stand-in returning a canned response."""

    def __init__(self, response: httpx.Response):
        self._response = response

    def get(self, url, headers=None):
        self.last_url = url
        # raise_for_status() requires the request to be attached
        self._response.request = httpx.Request("GET", url)
        return self._response


class TestValidateUrl:
    def test_accepts_http_and_https(self):
        assert validate_url("http://example.com/page") == "http://example.com/page"
        assert validate_url("https://example.com") == "https://example.com"

    def test_rejects_bad_schemes(self):
        for bad in ("ftp://x.com", "javascript:alert(1)", "not a url", "//relative"):
            with pytest.raises(ValueError):
                validate_url(bad)


class TestFetchPage:
    def test_parses_title_and_clean_text(self):
        client = _FakeClient(httpx.Response(200, text=FIXTURE_HTML))
        page = fetch_page("https://acme.com/docs", client=client)  # type: ignore[arg-type]
        assert isinstance(page, Page)
        assert page.title == "Product Docs — Acme"
        # scripts/styles/nav/footer stripped
        assert "secret" not in page.text
        assert "Site header banner" not in page.text
        assert "Pricing" not in page.text
        assert "Copyright" not in page.text
        # main content present
        assert "Welcome to Acme" in page.text
        assert "widgets" in page.text
        assert "Trusted by thousands of teams" in page.text

    def test_title_falls_back_to_og_or_host(self):
        html = "<html><body><p>no title here</p></body></html>"
        page = fetch_page("https://host.example/p", client=_FakeClient(httpx.Response(200, text=html)))  # type: ignore[arg-type]
        assert page.title == "host.example"

    def test_http_error_raises(self):
        client = _FakeClient(httpx.Response(404))
        with pytest.raises(httpx.HTTPStatusError):
            fetch_page("https://acme.com/missing", client=client)  # type: ignore[arg-type]


class TestCleanText:
    def test_collapses_whitespace(self):
        assert _clean_text("  hello \t world  \n\n\n  next") == "hello world\nnext"
