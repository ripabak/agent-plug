"""URL fetching + HTML→text parsing for RAG ingestion.

Goal: turn a web page into clean, readable text (with title) so the content
that reaches the vector store is tidy — no scripts, nav bars, or boilerplate.
"""
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from ..config import HTTP_FETCH_TIMEOUT

# Elements that never carry useful page content for RAG.
_STRIP_TAGS = [
    "script",
    "style",
    "noscript",
    "nav",
    "header",
    "footer",
    "iframe",
    "svg",
    "form",
    "aside",
    "button",
    "input",
    "select",
    "textarea",
    "template",
]

USER_AGENT = "AgentPlugBot/0.1 (+https://agent-plug.local; RAG crawler)"


@dataclass
class Page:
    """Parsed page content."""

    url: str
    title: str
    text: str


def validate_url(url: str) -> str:
    """Basic validation: must be an absolute http(s) URL. Raises ValueError."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url!r} (must be absolute http(s) URL)")
    return url.strip()


def _extract_title(soup: BeautifulSoup, url: str) -> str:
    """Prefer <title>, then og:title / h1, else fall back to host."""
    if soup.title and soup.title.string and soup.title.string.strip():
        return soup.title.string.strip()
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        content = og["content"]
        # BeautifulSoup may return a list when the attr has multiple values.
        if isinstance(content, list):
            content = " ".join(content)
        return str(content).strip()
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    return urlparse(url).netloc


def _clean_text(text: str) -> str:
    """Collapse blank lines / excessive whitespace into readable paragraphs."""
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def fetch_page(url: str, client: httpx.Client | None = None) -> Page:
    """Fetch and parse a URL into clean text. Sync (run via to_thread in async)."""
    url = validate_url(url)
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=HTTP_FETCH_TIMEOUT, follow_redirects=True)
    assert client is not None
    try:
        response = client.get(url, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        # Best-effort encoding; httpx already handles charset from headers.
        html = response.text
    finally:
        if own_client:
            client.close()

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_STRIP_TAGS):
        tag.decompose()

    title = _extract_title(soup, url)
    text = _clean_text(soup.get_text(separator="\n"))
    return Page(url=url, title=title, text=text)
