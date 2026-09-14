"""Headed BrowserScan through an HTTP proxy with a *named* (sticky) profile.

Cookies, local storage, and the sampled fingerprint stay on disk. Pair this
with a *sticky* proxy session (same exit IP), not a rotating pool.

Usage:
    export DISPLAY=:0
    export HEXIUM_BINARY_PATH="${HEXIUM_OUT}/chrome"
    "${HEXIUM_BINARY_PATH}" --version   # must print Chrome 151.0.7922.174
    export HEXIUM_PROXY='http://USER:PASS@host:port'
    # or host:port:USER:PASS  — sticky session id in the username if your provider uses one
    export HEXIUM_PROFILE=BrowserScan   # optional; default below
    export HEXIUM_GEOIP_TIMEOUT_SECONDS=30
    export HEXIUM_PERSONA=windows-chrome
    python examples/windows-chrome/browserscan-http-proxy-with-profile.py
"""

from __future__ import annotations

import os
import subprocess
from urllib.parse import quote, urlparse

from playwright.sync_api import Error as PlaywrightError

from hexium_browser import launch
from hexium_browser.download import ensure_binary

URL = "https://www.browserscan.net/"
GOTO_WAIT = "commit"
GOTO_TIMEOUT_MS = 60_000
DEFAULT_PROFILE = "BrowserScan"


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
        enc_user = quote(user, safe="")
        enc_pass = quote(password, safe="")
        return f"http://{enc_user}:{enc_pass}@{host}:{port}"
    return f"http://{raw}"


def _proxy_host_for_log(proxy: str) -> str:
    parsed = urlparse(proxy)
    if parsed.hostname and parsed.port:
        return f"{parsed.hostname}:{parsed.port}"
    if parsed.hostname:
        return parsed.hostname
    return "(invalid proxy host)"


def main() -> None:
    os.environ.setdefault("HEXIUM_GEOIP_TIMEOUT_SECONDS", "30")
    persona = os.environ.get("HEXIUM_PERSONA", "windows-chrome").strip() or "windows-chrome"
    profile = os.environ.get("HEXIUM_PROFILE", DEFAULT_PROFILE).strip() or DEFAULT_PROFILE
    proxy = _proxy_url()
    if not proxy:
        raise SystemExit(
            "Set HEXIUM_PROXY (http://USER:PASS@host:port or host:port:USER:PASS)"
        )

    binary = ensure_binary(allow_download=False)
    try:
        ver = subprocess.check_output(
            [os.fspath(binary), "--version"],
            text=True,
            timeout=15,
        ).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        ver = f"(could not run --version: {exc})"
    print(f"Binary: {binary}", flush=True)
    print(f"Version: {ver}", flush=True)
    print(
        f"Launching Hexium {persona} (headed, sticky profile={profile!r}, proxy)...",
        flush=True,
    )
    print(f"Proxy: {_proxy_host_for_log(proxy)}", flush=True)
    print(
        "Watch launch logs for 'WebRTC egress IP set to …'. "
        "Then chrome://version → Command Line must include --hexium-webrtc-ip= that IP.",
        flush=True,
    )

    browser = launch(
        headless=False,
        persona=persona,
        profile=profile,
        proxy=proxy,
        geoip=True,
        humanize=True,
    )
    try:
        page = browser.new_page()
        page.goto(URL, wait_until=GOTO_WAIT, timeout=GOTO_TIMEOUT_MS)
        print(f"URL:   {page.url}", flush=True)
        print(f"Title: {page.title()}", flush=True)
        print("BrowserScan open — review score in the window.", flush=True)
        print("Close window or Ctrl+C to quit.", flush=True)
        try:
            page.wait_for_event("close", timeout=0)
        except (PlaywrightError, KeyboardInterrupt):
            pass
    finally:
        try:
            browser.close()
        except PlaywrightError:
            pass


if __name__ == "__main__":
    main()
