"""Unit tests for source-marker parsing (citation URL safety)."""
from app.services.agent_session_service import parse_source_markers


def test_parses_well_formed_markers():
    text = (
        "[Source: https://example.com/pricing | Pricing] info "
        "[Source: https://example.com/faq] more"
    )
    sources = parse_source_markers(text)
    assert sources == [
        {"url": "https://example.com/pricing", "title": "Pricing"},
        {"url": "https://example.com/faq", "title": "https://example.com/faq"},
    ]


def test_skips_malformed_urls():
    """A mangled/regenerated URL (e.g. model glitch) must NOT become a source."""
    text = (
        "[Source: https://ripabak://ripabak://ripabak.github.io/posts/s.github.io/posts/solusi-storage-olusi-storage-iphone-penuhiphone-penuh/ | x] "
        "[Source: https://example.com | Good] "
        "[Source: ftp://example.com | bad scheme]"
    )
    sources = parse_source_markers(text)
    assert sources == [{"url": "https://example.com", "title": "Good"}]


def test_accepts_file_sources_for_uploaded_pdfs():
    text = "[Source: file://12/abc123.pdf | quarterly-report] revenue grew"
    assert parse_source_markers(text) == [
        {"url": "file://12/abc123.pdf", "title": "quarterly-report"}
    ]


def test_returns_empty_for_no_markers():
    assert parse_source_markers("no sources here [Source: incomplete") == []
    assert parse_source_markers("") == []


def test_accepts_text_sources():
    text = "[Source: text://abc123 | FAQ Internal] Return policy is thirty days."
    assert parse_source_markers(text) == [
        {"url": "text://abc123", "title": "FAQ Internal"}
    ]
