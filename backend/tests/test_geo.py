"""Tests for geo detection (MaxMind GeoLite2 Country DB, offline)."""
import geoip2.errors
import pytest

from app.services import geo


class FakeCountry:
    def __init__(self, iso_code):
        self.iso_code = iso_code


class FakeReader:
    """Minimal stand-in for geoip2.database.Reader."""

    def __init__(self, mapping=None, error=None):
        self.mapping = mapping or {}
        self.error = error

    def country(self, ip):
        if self.error:
            raise self.error
        if ip in self.mapping:
            return type("R", (), {"country": FakeCountry(self.mapping[ip])})()
        raise geoip2.errors.AddressNotFoundError("no data")


# ------------------------------------------------------------- normalize_ip
@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",  # loopback
        "10.0.0.5",  # private
        "192.168.1.10",  # private
        "172.16.0.1",  # private
        "169.254.1.1",  # link-local
        "::1",  # IPv6 loopback
        "fc00::1",  # IPv6 private
        "",  # empty
        None,
        "not-an-ip",
        "unknown",
        "testclient",  # httpx ASGITransport peer name in tests
    ],
)
def test_normalize_ip_rejects_private_or_invalid(ip):
    assert geo._normalize_ip(ip) is None


@pytest.mark.parametrize("ip", ["8.8.8.8", "1.1.1.1", "2001:4860:4860::8888"])
def test_normalize_ip_keeps_public(ip):
    assert geo._normalize_ip(ip) == ip


# ----------------------------------------------------------- resolve_country
def test_resolve_country_skips_private_ips(monkeypatch):
    monkeypatch.setattr(geo, "_get_reader", lambda: FakeReader({"8.8.8.8": "US"}))
    assert geo.resolve_country("127.0.0.1") is None
    assert geo.resolve_country("10.0.0.5") is None


def test_resolve_country_returns_code(monkeypatch):
    monkeypatch.setattr(geo, "_get_reader", lambda: FakeReader({"8.8.8.8": "US"}))
    assert geo.resolve_country("8.8.8.8") == "US"


def test_resolve_country_unknown_ip_returns_none(monkeypatch):
    monkeypatch.setattr(geo, "_get_reader", lambda: FakeReader({}))
    assert geo.resolve_country("203.0.113.99") is None


def test_resolve_country_reader_errors_are_graceful(monkeypatch):
    monkeypatch.setattr(
        geo, "_get_reader", lambda: FakeReader(error=RuntimeError("db corrupt"))
    )
    assert geo.resolve_country("8.8.8.8") is None


def test_resolve_country_disabled_via_config(monkeypatch):
    """When the reader is unavailable (disabled / missing DB) -> None."""
    monkeypatch.setattr(geo, "_get_reader", lambda: None)
    assert geo.resolve_country("8.8.8.8") is None


def test_get_reader_none_when_db_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(geo, "GEOIP_ENABLED", True)
    monkeypatch.setattr(geo, "GEOIP_DB_PATH", str(tmp_path / "nope.mmdb"))
    geo._reader = None
    try:
        assert geo._get_reader() is None
        # also resolved gracefully at the API level
        assert geo.resolve_country("8.8.8.8") is None
    finally:
        geo._reader = None


# ------------------------------------------------- integration with the real DB
def test_resolve_country_against_bundled_db(monkeypatch):
    """The committed GeoLite2 DB maps well-known public IPs to countries."""
    monkeypatch.setattr(geo, "GEOIP_ENABLED", True)
    monkeypatch.setattr(geo, "GEOIP_DB_PATH", "GeoLite2-Country.mmdb")
    geo._reader = None
    try:
        assert geo.resolve_country("8.8.8.8") == "US"
        # private IPs never hit the DB
        assert geo.resolve_country("127.0.0.1") is None
    finally:
        geo._reader = None


# ----------------------------------------------------------- request_client_ip
def test_request_client_ip_prefers_forwarded_header():
    req = type("Req", (), {"headers": {"x-forwarded-for": "203.0.113.9, 10.0.0.1"}, "client": None})()
    assert geo.request_client_ip(req) == "203.0.113.9"


def test_request_client_ip_falls_back_to_socket_peer():
    req = type("Req", (), {"headers": {}, "client": type("C", (), {"host": "127.0.0.1"})()})()
    assert geo.request_client_ip(req) == "127.0.0.1"


def test_request_client_ip_none_when_unavailable():
    req = type("Req", (), {"headers": {}, "client": None})()
    assert geo.request_client_ip(req) is None
