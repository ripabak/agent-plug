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


class TestLinksPreserved:
    LINKED_HTML = """<!DOCTYPE html>
<html>
<head><title>Linky</title></head>
<body>
  <main>
    <p>See <a href="/docs/guide">the guide</a> and
       <a href="https://example.com/abs">absolute link</a>.</p>
    <p>No href: <a>plain</a>; empty href: <a href="">nothing</a>.</p>
    <p>Icon only: <a href="/icon.svg"></a></p>
  </main>
</body>
</html>
"""

    def test_content_links_become_markdown_links(self):
        page = fetch_page(
            "https://acme.com/docs/start",
            client=_FakeClient(httpx.Response(200, text=self.LINKED_HTML)),  # type: ignore[arg-type]
        )
        # relative href resolved against the page URL
        assert "[the guide](https://acme.com/docs/guide)" in page.text
        # absolute href kept as-is
        assert "[absolute link](https://example.com/abs)" in page.text
        # anchors without a usable href stay as plain text
        assert "plain" in page.text
        assert "nothing" in page.text
        assert "(plain)" not in page.text and "(nothing)" not in page.text
        # image-only anchor falls back to the raw href as link text
        assert "[/icon.svg](https://acme.com/icon.svg)" in page.text

    def test_base_href_is_honoured(self):
        html = (
            '<html><head><title>Base</title>'
            '<base href="https://cdn.acme.com/"></head>'
            '<body><p><a href="files/a.pdf">file</a></p></body></html>'
        )
        page = fetch_page(
            "https://acme.com/docs",
            client=_FakeClient(httpx.Response(200, text=html)),  # type: ignore[arg-type]
        )
        assert "[file](https://cdn.acme.com/files/a.pdf)" in page.text

    def test_nav_links_still_stripped_as_boilerplate(self):
        # nav/header/footer are decomposed before link inlining, so their
        # links must NOT survive into the text.
        page = fetch_page("https://acme.com/docs", client=_FakeClient(httpx.Response(200, text=FIXTURE_HTML)))  # type: ignore[arg-type]
        assert "Pricing" not in page.text
        assert "[Pricing](https://acme.com/pricing)" not in page.text


class TestCleanText:
    def test_collapses_whitespace(self):
        assert _clean_text("  hello \t world  \n\n\n  next") == "hello world\nnext"
