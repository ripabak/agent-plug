"""Client geo detection (IP -> country code) for usage analytics.

Uses the bundled MaxMind GeoLite2 Country database (`GeoLite2-Country.mmdb`)
— fully offline, no API key, no network calls. The reader is loaded lazily
once and reused (read-only + thread-safe). Private/local addresses are
skipped (GeoLite2 has no mapping for them anyway), and every failure
degrades gracefully to `None`, so geo can never break the chat runtime.
"""
import ipaddress
import os
import threading
from typing import Any

import geoip2.database

from ..config import GEOIP_DB_PATH, GEOIP_ENABLED

_disabled = object()
_reader: Any = None  # None = not loaded yet, _disabled = unusable
_lock = threading.Lock()


def _get_reader() -> geoip2.database.Reader | None:
    """Lazy singleton reader; None when disabled or the DB file is missing."""
    global _reader
    if _reader is None:
        with _lock:
            if _reader is None:
                if not GEOIP_ENABLED or not os.path.exists(GEOIP_DB_PATH):
                    _reader = _disabled
                else:
                    try:
                        _reader = geoip2.database.Reader(GEOIP_DB_PATH)
                    except Exception:
                        _reader = _disabled
    return None if _reader is _disabled else _reader


def _normalize_ip(value: str | None) -> str | None:
    """Trim + validate an IP; None for private/reserved/loopback addresses."""
    if not value:
        return None
    ip = value.strip()
    if not ip or ip.lower() in ("unknown", "testclient"):
        return None
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return None
    if (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
    ):
        return None
    return ip


def resolve_country(ip: str | None) -> str | None:
    """ISO alpha-2 country code for a client IP (None when unknown)."""
    ip = _normalize_ip(ip)
    if ip is None:
        return None
    reader = _get_reader()
    if reader is None:
        return None
    try:
        response = reader.country(ip)
        return response.country.iso_code or None
    except Exception:  # unknown IP, corrupt DB, anything — never break chat
        return None


def request_client_ip(request) -> str | None:
    """Best-effort client IP: first X-Forwarded-For hop, else socket peer.

    X-Forwarded-For is trusted for analytics purposes only — on a directly
    exposed server the header could be spoofed, which is acceptable for
    usage stats (and harmless: private/spoofed values just yield no country).
    """
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        first = fwd.split(",")[0].strip()
        if first:
            return first
    if request.client is not None:
        return request.client.host
    return None
