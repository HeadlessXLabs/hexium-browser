"""Quick Hexium demo: open Google in a headed window (real profile + tab)."""

from playwright.sync_api import Error as PlaywrightError

from hexium_browser import launch


def main() -> None:
    print("Launching Hexium (headed, humanize on, persistent profile)...", flush=True)
    browser = launch(headless=False, humanize=True, show_cursor=True)
    try:
        page = browser.new_page()
        page.goto("https://www.google.com", wait_until="domcontentloaded")
        print(f"Title: {page.title()}", flush=True)
        print(f"URL:   {page.url}", flush=True)
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
        print("Done.", flush=True)


if __name__ == "__main__":
    main()
