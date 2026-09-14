from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote, urlparse

from playwright.sync_api import Error as PlaywrightError

from hexium_browser import launch

URL = "https://whoer.net/"
GOTO_WAIT = "commit"
GOTO_TIMEOUT_MS = 60_000
SETTLE_MS = 20_000
REPO_ROOT = Path(__file__).resolve().parent.parent
SHOT_DIR = REPO_ROOT / "assets" / "screenshots"


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


def whoer_launch_kwargs(*, headless: bool, persona: str) -> dict:
    """whoer.net smoke: rotating HTTP proxy + new random profile each run.

    Never pass ``profile=`` — that is sticky. Use a rotating proxy username
    (no session pin) in ``HEXIUM_PROXY``.
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


def run_whoer(*, persona: str, screenshot_name: str) -> None:
    shot_path = SHOT_DIR / screenshot_name
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    keep_open = os.environ.get("HEXIUM_WHOER_KEEP_OPEN", "").strip() in ("1", "true", "yes")
    kw = whoer_launch_kwargs(headless=False, persona=persona)
    print(
        f"Launching {persona} headed whoer.net "
        "(rotate proxy via HEXIUM_PROXY, ephemeral random profile)...",
        flush=True,
    )
    browser = launch(**kw)
    try:
        page = browser.new_page()
        page.goto(URL, wait_until=GOTO_WAIT, timeout=GOTO_TIMEOUT_MS)
        print(f"URL: {page.url}", flush=True)
        print(f"Settling {SETTLE_MS // 1000}s before screenshot...", flush=True)
        page.wait_for_timeout(SETTLE_MS)
        page.screenshot(path=str(shot_path), full_page=True)
        print(f"Screenshot: {shot_path}", flush=True)
        print(f"Title: {page.title()}", flush=True)
        if keep_open:
            print("Close window or Ctrl+C.", flush=True)
            try:
                page.wait_for_event("close", timeout=0)
            except (PlaywrightError, KeyboardInterrupt):
                pass
    finally:
        try:
            browser.close()
        except PlaywrightError:
            pass
