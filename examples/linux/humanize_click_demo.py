"""Headed humanize demo: blue highlighter on a white page with red buttons."""

from pathlib import Path

from playwright.sync_api import Error as PlaywrightError

from hexium_browser import launch
from hexium_browser.artifacts import SCREENSHOTS_DIR, finalize_recording, recording_kwargs

HTML = Path(__file__).resolve().parent.parent / "assets" / "mouse_demo.html"
CLICKS = 8
RECORDING_NAME = "humanize_click_demo"


def _move_count(page) -> int:
    raw = page.evaluate(
        "document.documentElement.getAttribute('data-moves') || '0'"
    )
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def main() -> None:
    rec = recording_kwargs(RECORDING_NAME)
    print("Launching Hexium (headed, humanize on, recording)...", flush=True)
    print(f"Page: {HTML}", flush=True)
    print(
        f"Video size: {rec['viewport']['width']}x{rec['viewport']['height']}",
        flush=True,
    )
    browser = launch(headless=False, humanize=True, show_cursor=True, **rec)
    video = None
    try:
        page = browser.new_page()
        video = page.video
        page.goto(HTML.as_uri(), wait_until="domcontentloaded")
        page.wait_for_selector("button.button", timeout=10_000)

        page.mouse.move(40, 40)
        before = _move_count(page)
        page.mouse.move(900, 500)
        after = _move_count(page)
        delta = after - before
        print(f"Trajectory mouse.move(40,40) → (900,500): {delta} mousemove events", flush=True)
        if delta >= 10:
            print("  PASS: humanize emitted a path", flush=True)
        else:
            print("  FAIL: expected >= 10 intermediate points", flush=True)

        for i in range(CLICKS):
            print(f"Humanized click {i + 1}/{CLICKS}...", flush=True)
            page.locator("button.button").first.click()

        n = _move_count(page)
        print(f"Total mousemove events: {n}", flush=True)
        shot = SCREENSHOTS_DIR / "humanize_click_demo.png"
        page.screenshot(path=str(shot))
        print(f"Screenshot: {shot}", flush=True)
        print("Waiting 5 seconds...", flush=True)
        try:
            page.wait_for_timeout(5_000)
        except PlaywrightError:
            pass
    finally:
        try:
            browser.close()
        except PlaywrightError:
            pass
        dest = finalize_recording(video, RECORDING_NAME)
        if dest is not None:
            print(f"Recording: {dest}", flush=True)
        else:
            print("Recording failed: no video file", flush=True)
        print("Done.", flush=True)


if __name__ == "__main__":
    main()
