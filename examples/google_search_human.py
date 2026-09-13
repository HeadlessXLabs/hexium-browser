"""Google homepage: humanized icon click, type a query, click search.

Blue in-page highlighter follows the CDP mouse (OS cursor never moves).
Each variant records to a stable ``assets/recordings/<name>.webm``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from hexium_browser import launch
from hexium_browser.artifacts import SCREENSHOTS_DIR, finalize_recording, recording_kwargs

SEARCH_ICON = "div.RNNXgb button.plR5qb"
SEARCH_BOX = 'textarea[name="q"]'
SEARCH_SUBMIT = "form button.plR5qb.VzUPFe.PHjFye.Sw4CSc"
QUERY = "Nextjs Latest version"
WAIT_MS = 5_000
HIGHLIGHTER = Path(__file__).resolve().parent / "assets" / "cursor_highlighter.js"
RECORDING_NAME = "google_search_human"


def _install_highlighter(page: Any) -> None:
    js = HIGHLIGHTER.read_text(encoding="utf-8")
    try:
        page.add_init_script(js)
    except PlaywrightError:
        pass
    try:
        page.evaluate(js)
    except PlaywrightError:
        pass


def dismiss_consent(page: Any) -> None:
    for sel in (
        'button:has-text("Accept all")',
        'button:has-text("I agree")',
        'button:has-text("Reject all")',
        "#L2AGLb",
    ):
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=1500):
                loc.click()
                return
        except PlaywrightTimeoutError:
            continue
        except PlaywrightError:
            continue


def run_search(page: Any) -> None:
    page.goto("https://www.google.com", wait_until="domcontentloaded")
    _install_highlighter(page)
    dismiss_consent(page)
    page.wait_for_selector(SEARCH_BOX, state="visible", timeout=20_000)

    print("Watch the blue ring, not the OS pointer...", flush=True)
    print("Humanized click: search-bar icon (button.plR5qb / div.bvUkz)...", flush=True)
    page.locator(SEARCH_ICON).first.click()

    print("Humanized click: search box, then type...", flush=True)
    page.locator(SEARCH_BOX).first.click()
    page.type(SEARCH_BOX, QUERY)

    print("Humanized click: search submit (button.plR5qb.VzUPFe / div.bvUkz)...", flush=True)
    page.locator(SEARCH_SUBMIT).first.click()
    _install_highlighter(page)

    print(f"Waiting {WAIT_MS // 1000} seconds...", flush=True)
    try:
        page.wait_for_timeout(WAIT_MS)
    except PlaywrightError:
        pass


def run(
    *,
    headless: bool = False,
    user_data_dir: str | Path | None = None,
    recording_name: str = RECORDING_NAME,
) -> None:
    extra = f", profile={user_data_dir}" if user_data_dir else ""
    rec = recording_kwargs(recording_name)
    print(
        f"Launching Hexium (headless={headless}, humanize on, highlighter, recording{extra})...",
        flush=True,
    )
    print(
        f"Video size: {rec['viewport']['width']}x{rec['viewport']['height']}",
        flush=True,
    )
    kwargs: dict[str, Any] = {
        "headless": headless,
        "humanize": True,
        "show_cursor": not headless,
        **rec,
    }
    if user_data_dir is not None:
        kwargs["user_data_dir"] = str(user_data_dir)
    browser = launch(**kwargs)
    video = None
    try:
        page = browser.new_page()
        video = page.video
        _install_highlighter(page)
        run_search(page)
        shot = SCREENSHOTS_DIR / f"{recording_name}.png"
        page.screenshot(path=str(shot))
        print(f"Screenshot: {shot}", flush=True)
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


def main() -> None:
    run(headless=False, recording_name=RECORDING_NAME)


if __name__ == "__main__":
    main()
