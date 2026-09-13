"""Headed Windows-on-Linux Hexium: open google.com and leave the window open.

Usage:
    export DISPLAY=:0
    export HEXIUM_BINARY_PATH=/path/to/Hexium/chrome
    python examples/windows-chrome/win-google.py
"""

from playwright.sync_api import Error as PlaywrightError

from hexium_browser import launch

URL = "https://www.google.com/ncr"
GOTO_WAIT = "commit"
GOTO_TIMEOUT_MS = 60_000


def main() -> None:
    print("Launching Hexium windows-chrome (headed)...", flush=True)
    browser = launch(headless=False, persona="windows-chrome")
    try:
        page = browser.new_page()
        try:
            page.goto(URL, wait_until=GOTO_WAIT, timeout=GOTO_TIMEOUT_MS)
        except PlaywrightError as exc:
            print(f"Navigation note: {exc}", flush=True)
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
