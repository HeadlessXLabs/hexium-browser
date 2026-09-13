"""Headed windows-chrome + HTTP proxy smoke test (google.com).

Usage:
    export DISPLAY=:0
    export HEXIUM_BINARY_PATH=/path/to/Hexium/chrome
    export HEXIUM_PROXY='http://user:pass@host:10000'
    export HEXIUM_GEOIP_TIMEOUT_SECONDS=15
    python examples/windows-chrome/win-google-http-proxy.py
"""

from __future__ import annotations

import os

from playwright.sync_api import Error as PlaywrightError

from hexium_browser import launch

URL = "https://www.google.com/ncr"
GOTO_WAIT = "commit"
GOTO_TIMEOUT_MS = 60_000


def _proxy_url() -> str | None:
    raw = os.environ.get("HEXIUM_PROXY", "").strip()
    if not raw:
        return None
    if "://" in raw:
        return raw
    return f"http://{raw}"


def main() -> None:
    os.environ.setdefault("HEXIUM_GEOIP_TIMEOUT_SECONDS", "15")
    proxy = _proxy_url()
    if not proxy:
        raise SystemExit("Set HEXIUM_PROXY (http://user:pass@host:port)")

    print("Launching Hexium windows-chrome (headed, proxy)...", flush=True)
    print(f"Proxy: {proxy.split('@')[-1]}", flush=True)

    browser = launch(
        headless=False,
        persona="windows-chrome",
        proxy=proxy,
        geoip=True,
        ephemeral=True,
    )
    try:
        page = browser.new_page()
        try:
            page.goto(URL, wait_until=GOTO_WAIT, timeout=GOTO_TIMEOUT_MS)
        except PlaywrightError as exc:
            print(f"Navigation note: {exc}", flush=True)
            print("Google often blocks or stalls on proxy IPs — use browserscan-http-proxy.py to test.", flush=True)
        print(f"Title: {page.title()}", flush=True)
        print(f"URL:   {page.url}", flush=True)
        print(
            page.evaluate(
                "() => ({platform: navigator.platform, ua: navigator.userAgent, "
                "webgl: (() => { const c = document.createElement('canvas'); "
                "const gl = c.getContext('webgl'); if (!gl) return null; "
                "const ext = gl.getExtension('WEBGL_debug_renderer_info'); "
                "return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : null; })()})"
            ),
            flush=True,
        )
        print("Window stays open. Close it or Ctrl+C to quit.", flush=True)
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
