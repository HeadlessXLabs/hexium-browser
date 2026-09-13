from __future__ import annotations

import os
from urllib.parse import quote, urlparse

URL = "https://www.allegro.pl"
GOTO_WAIT = "commit"
GOTO_TIMEOUT_MS = 60_000
WANDER_MS = 2_000
WANDER_POINTS = [(160, 180), (520, 240), (380, 420), (720, 200), (280, 360)]


def _proxy_url() -> str | None:
    raw = os.environ.get("HEXIUM_PROXY", "").strip()
    if not raw:
        return None
    if "://" in raw:
        parsed = urlparse(raw)
        if not parsed.hostname:
            raise SystemExit(
                "HEXIUM_PROXY looks like a URL but has no host. "
                "Use http://USER:PASS@host:port (the @ before the host is required)."
            )
        return raw
    if "@" in raw:
        return f"http://{raw}"
    parts = raw.split(":")
    if len(parts) == 4:
        host, port, user, password = parts
        return f"http://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}"
    return f"http://{raw}"


def allegro_launch_kwargs(*, headless: bool, persona: str = "linux-native") -> dict:
    """Allegro smoke: proxy + GeoIP + humanize + a new random profile each run.

    Never pass ``profile=`` / ``user_data_dir=`` here — those are sticky.
    ``ephemeral=True`` mints ``hexium-session-*`` and a new seed.
    """
    os.environ.setdefault("HEXIUM_GEOIP_TIMEOUT_SECONDS", "30")
    kwargs: dict = {
        "headless": headless,
        "persona": persona,
        "humanize": True,
        "geoip": True,
        "ephemeral": True,
        "show_cursor": False,
    }
    proxy = _proxy_url()
    if proxy:
        kwargs["proxy"] = proxy
    return kwargs
