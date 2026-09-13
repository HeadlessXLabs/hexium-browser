"""Persistent context example: cookies and localStorage survive across sessions."""

from hexium_browser import launch

PROFILE_NAME = "example-persistent"

# Session 1 — set some state
print("=== Session 1: Setting state ===")
print("Launching stealth browser...", flush=True)
browser = launch(profile=PROFILE_NAME, headless=False, humanize=True, show_cursor=True)
page = browser.new_page()
page.goto("https://example.com")
page.evaluate("document.cookie = 'session=abc123; path=/; max-age=3600'")
page.evaluate("localStorage.setItem('user', 'returning')")
print(f"Cookie: {page.evaluate('document.cookie')}")
ls_val = page.evaluate("localStorage.getItem('user')")
print(f"localStorage: {ls_val}")
browser.close()

# Session 2 — state is restored
print("\n=== Session 2: Verifying persistence ===")
print("Launching stealth browser...", flush=True)
browser = launch(profile=PROFILE_NAME, headless=False, humanize=True, show_cursor=True)
page = browser.new_page()
page.goto("https://example.com")
print(f"Cookie: {page.evaluate('document.cookie')}")
ls_val = page.evaluate("localStorage.getItem('user')")
print(f"localStorage: {ls_val}")
browser.close()

print("\nDone!")
