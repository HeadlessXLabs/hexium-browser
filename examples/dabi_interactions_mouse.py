"""Humanize on DeviceAndBrowserInfo interaction oracle, with Hexium blue highlighter.

https://deviceandbrowserinfo.com/are_you_a_bot_interactions

Playwright/CDP never moves the OS cursor. This injects the same blue ring as
humanize_click_demo.py so you can watch the path. Debug only — detectable.
"""

from pathlib import Path

from playwright.sync_api import Error as PlaywrightError

from hexium_browser import launch
from hexium_browser.artifacts import SCREENSHOTS_DIR, finalize_recording, recording_kwargs

URL = "https://deviceandbrowserinfo.com/are_you_a_bot_interactions"
HIGHLIGHTER = Path(__file__).resolve().parent / "assets" / "cursor_highlighter.js"
RECORDING_NAME = "dabi_interactions_mouse"


def _install_highlighter(page) -> None:
    js = HIGHLIGHTER.read_text(encoding="utf-8")
    try:
        page.add_init_script(js)
    except PlaywrightError:
        pass
    try:
        page.evaluate(js)
    except PlaywrightError:
        pass


def main() -> None:
    rec = recording_kwargs(RECORDING_NAME)
    print("Launching Hexium (headed, humanize on, blue highlighter, recording)...", flush=True)
    print(
        f"Video size: {rec['viewport']['width']}x{rec['viewport']['height']}",
        flush=True,
    )
    browser = launch(headless=False, humanize=True, show_cursor=True, **rec)
    video = None
    try:
        page = browser.new_page()
        video = page.video
        _install_highlighter(page)
        page.goto(URL, wait_until="domcontentloaded")
        _install_highlighter(page)
        page.wait_for_selector("#email", state="visible", timeout=20_000)

        print("Watch the blue ring, not the OS pointer...", flush=True)
        page.mouse.move(180, 160)
        page.mouse.move(820, 280)
        page.mouse.move(420, 520)

        print("Login form (mouse + type scored by the page)...", flush=True)
        page.click("#email")
        page.type("#email", "test@example.com")
        page.click("#password")
        page.type("#password", "SecurePass!123")
        page.click('#loginForm button[type="submit"]')

        shot = SCREENSHOTS_DIR / "dabi_interactions_mouse.png"
        page.screenshot(path=str(shot), full_page=True)
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
