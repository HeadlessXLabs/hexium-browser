"""Check reCAPTCHA v3 score with stealth browser.

Visits Google's reCAPTCHA demo page and extracts the score.
Expected: 0.9 (human-level) with hexium_browser.
Default Playwright typically scores 0.1-0.3.
"""

import re

from hexium_browser import launch
from hexium_browser.artifacts import SCREENSHOTS_DIR, ensure_artifact_dirs

print("Launching stealth browser...", flush=True)
# Overlay is a detector tell on stealth oracles — keep it off.
browser = launch(headless=True, humanize=True, show_cursor=False)
page = browser.new_page()

# Google's official reCAPTCHA v3 demo — scores automatically on page load.
page.goto("https://recaptcha-demo.appspot.com/recaptcha-v3-request-scores.php")

# The score renders only after an async token + backend-verify round-trip,
# which can finish *after* "networkidle". Wait for the actual result text
# instead of a proxy signal, or the screenshot races the scoring.
page.wait_for_function(
    "() => document.body.innerText.includes('Received response from our backend')",
    timeout=20000,
)

# Extract score from the rendered response
match = re.search(r'"score":\s*([0-9.]+)', page.inner_text("body"))
print(f"reCAPTCHA v3 score: {match.group(1) if match else 'not found'}")
print(f"URL: {page.url}")

ensure_artifact_dirs()
page.screenshot(path=str(SCREENSHOTS_DIR / "recaptcha_score.png"))
print(f"Screenshot saved: {SCREENSHOTS_DIR / 'recaptcha_score.png'}")

browser.close()
