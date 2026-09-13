#!/usr/bin/env python3
"""Minimal Hexium oracle smoke test.

Prints key navigator signals after launch. Optionally visit a detection URL.

Usage:
    python examples/oracle_smoke.py
    python examples/oracle_smoke.py --url https://bot.sannysoft.com
"""

from __future__ import annotations

import argparse
import json
import sys

from hexium_browser import launch


def main() -> int:
    parser = argparse.ArgumentParser(description="Hexium oracle smoke test")
    parser.add_argument(
        "--url",
        default="about:blank",
        help="Optional page to open (e.g. https://bot.sannysoft.com)",
    )
    parser.add_argument("--headed", action="store_true", help="Run headed instead of headless")
    args = parser.parse_args()

    print("Launching Hexium browser (humanize on, fingerprint=test-seed)...", flush=True)
    # Overlay is a detector tell on stealth oracles — keep it off.
    browser = launch(
        headless=not args.headed,
        humanize=True,
        show_cursor=False,
        fingerprint="test-seed",
    )
    page = browser.new_page()

    if args.url != "about:blank":
        print(f"Navigating to {args.url}...", flush=True)
        page.goto(args.url, wait_until="domcontentloaded", timeout=60000)

    signals = page.evaluate(
        """() => ({
            webdriver: navigator.webdriver,
            plugins: navigator.plugins.length,
            chrome: typeof window.chrome !== 'undefined',
            platform: navigator.platform,
            userAgent: navigator.userAgent,
        })"""
    )

    print("\nOracle signals:")
    print(json.dumps(signals, indent=2))

    browser.close()
    print("\nSmoke test complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
