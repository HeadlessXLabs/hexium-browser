"""Headed Allegro.pl — linux-native, HTTP proxy, ephemeral random profile.

Usage:
    export DISPLAY=:0
    export HEXIUM_BINARY_PATH="${HEXIUM_OUT}/chrome"
    export HEXIUM_PROXY='http://USER:PASS@host:port'
    python examples/linux-native/allegro_pl_headed_http_proxy_ephemeral_random_profile.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from allegro_common import (
    GOTO_TIMEOUT_MS,
    GOTO_WAIT,
    URL,
    WANDER_MS,
    WANDER_POINTS,
    allegro_launch_kwargs,
)
from hexium_browser import launch


def _wander(page, duration_ms: int, points: list[tuple[int, int]]) -> None:
    step = max(120, duration_ms // (len(points) + 1))
    try:
        for x, y in points:
            page.mouse.move(x, y)
            page.wait_for_timeout(step)
    except PlaywrightError:
        pass


def main() -> None:
    kw = allegro_launch_kwargs(headless=False, persona="linux-native")
    print(
        "Launching linux-native headed Allegro (proxy if HEXIUM_PROXY, ephemeral random profile)...",
        flush=True,
    )
    browser = launch(**kw)
    try:
        page = browser.new_page()
        page.goto(URL, wait_until=GOTO_WAIT, timeout=GOTO_TIMEOUT_MS)
        _wander(page, WANDER_MS, WANDER_POINTS)
        print(f"URL: {page.url}", flush=True)
        print(f"Title: {page.title()}", flush=True)
        print("Close window or Ctrl+C.", flush=True)
        try:
            page.wait_for_event("close", timeout=0)
        except (PlaywrightError, KeyboardInterrupt):
            pass
    finally:
        browser.close()


if __name__ == "__main__":
    main()
