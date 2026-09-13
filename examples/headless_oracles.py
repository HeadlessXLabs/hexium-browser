"""Headless oracle walk: Vercel detector, then Infosimples, same tab, record video.

Infosimples Time Elapse is fixed in Blink (alert() dwells 1100–1600ms). No
Playwright dialog handler.
"""

from __future__ import annotations

from playwright.sync_api import Error as PlaywrightError

from hexium_browser import launch
from hexium_browser.artifacts import SCREENSHOTS_DIR, finalize_recording, recording_kwargs

VERCEL = "https://headless-detector.vercel.app/"
INFOSIMPLES = "https://infosimples.github.io/detect-headless/"


def _wander(page, duration_ms: int, points: list[tuple[int, int]]) -> None:
    step = max(200, duration_ms // (len(points) + 1))
    try:
        page.wait_for_timeout(step)
        for x, y in points:
            page.mouse.move(x, y)
            page.wait_for_timeout(step)
    except PlaywrightError:
        pass


def _print_vercel_score(page) -> None:
    try:
        score = page.evaluate(
            """() => ({
              score: window.__headlessDetectionScore
                ?? document.documentElement.getAttribute('data-headless-score'),
              title: document.title,
            })"""
        )
        print(f"Vercel detector: {score}", flush=True)
    except PlaywrightError:
        pass


def _print_infosimples(page) -> None:
    try:
        rows = page.evaluate(
            """() => Array.from(document.querySelectorAll('table tr')).slice(0, 24).map(tr =>
              Array.from(tr.querySelectorAll('th,td')).map(c => (c.textContent || '').trim()).filter(Boolean)
            ).filter(r => r.length)"""
        )
        print("Infosimples rows:", flush=True)
        for row in rows or []:
            print(f"  {row}", flush=True)
    except PlaywrightError:
        pass


def run(*, recording_name: str, persona: str | None = None) -> None:
    rec = recording_kwargs(recording_name)
    extra: dict = {}
    if persona is not None:
        extra["persona"] = persona
    print(
        f"Launching Hexium (headless, humanize, recording={recording_name}"
        f"{', persona=' + persona if persona else ''})...",
        flush=True,
    )
    print(
        f"Video size: {rec['viewport']['width']}x{rec['viewport']['height']}",
        flush=True,
    )
    browser = launch(
        headless=True,
        humanize=True,
        show_cursor=False,
        geoip=False,
        **rec,
        **extra,
    )
    video = None
    try:
        page = browser.new_page()
        video = page.video

        print(f"Open {VERCEL} (wait 5s, move mouse)...", flush=True)
        page.goto(VERCEL, wait_until="domcontentloaded")
        _wander(page, 5_000, [(180, 160), (640, 280), (420, 420), (760, 200)])
        _print_vercel_score(page)
        shot_a = SCREENSHOTS_DIR / f"{recording_name}_vercel.png"
        try:
            page.screenshot(path=str(shot_a), full_page=True)
            print(f"Screenshot: {shot_a}", flush=True)
        except PlaywrightError as exc:
            print(f"Screenshot skipped: {exc}", flush=True)

        print(f"Same tab → {INFOSIMPLES} (wait 10s, move mouse)...", flush=True)
        page.goto(INFOSIMPLES, wait_until="domcontentloaded", timeout=60_000)
        _wander(
            page,
            10_000,
            [(120, 140), (500, 260), (280, 480), (700, 180), (360, 320)],
        )
        _print_infosimples(page)
        shot_b = SCREENSHOTS_DIR / f"{recording_name}_infosimples.png"
        try:
            page.screenshot(path=str(shot_b), full_page=True)
            print(f"Screenshot: {shot_b}", flush=True)
        except PlaywrightError as exc:
            print(f"Screenshot skipped: {exc}", flush=True)
    finally:
        try:
            browser.close()
        except PlaywrightError:
            pass
        dest = finalize_recording(video, recording_name)
        if dest is not None:
            print(f"Recording: {dest}", flush=True)
        else:
            print("Recording failed: no video file", flush=True)
        print("Done.", flush=True)
