#!/usr/bin/env python3
"""Prove linux-chrome persona after an overlay rebuild.

Writes <profile>/persona.json, prints live Intl / navigator / screen / WebGL,
opens https://example.com, and checks that GPU stays the host (no Direct3D)
while hardware/screen follow the sampled JSON.

Usage:
    python examples/linux-chrome/linux_chrome_persona.py
    python examples/linux-chrome/linux_chrome_persona.py --headed
    python examples/linux-chrome/linux_chrome_persona.py --proxy http://127.0.0.1:8888
    python examples/linux-chrome/linux_chrome_persona.py --twice
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError

from hexium_browser import launch
from hexium_browser.artifacts import SCREENSHOTS_DIR, ensure_artifact_dirs
from hexium_browser.config import get_profiles_root

WAIT_MS = 120_000

_READ_SIGNALS = """() => {
  const webgl = (() => {
    const c = document.createElement('canvas');
    const gl = c.getContext('webgl') || c.getContext('experimental-webgl');
    if (!gl) return null;
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    return {
      vendor: ext ? gl.getParameter(ext.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR),
      renderer: ext
        ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)
        : gl.getParameter(gl.RENDERER),
    };
  })();
  return {
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    language: navigator.language,
    languages: [...navigator.languages],
    platform: navigator.platform,
    userAgent: navigator.userAgent,
    hardwareConcurrency: navigator.hardwareConcurrency,
    deviceMemory: navigator.deviceMemory,
    screen: {
      width: screen.width,
      height: screen.height,
      availWidth: screen.availWidth,
      availHeight: screen.availHeight,
      colorDepth: screen.colorDepth,
    },
    webgl,
  };
}"""


def _one_tab(browser):
    pages = []
    for ctx in getattr(browser, "contexts", []) or []:
        pages.extend(getattr(ctx, "pages", []) or [])
    if not pages:
        return browser.new_page()
    keep = pages[0]
    for extra in pages[1:]:
        try:
            extra.close()
        except Exception:
            pass
    return keep


def _load_persona_json(profile: Path) -> dict:
    path = profile / "persona.json"
    if not path.is_file():
        raise SystemExit(f"missing {path} — launch did not write a linux-chrome persona file")
    return json.loads(path.read_text(encoding="utf-8"))


def _print_block(title: str, payload: object) -> None:
    print(f"\n=== {title} ===", flush=True)
    print(json.dumps(payload, indent=2), flush=True)


def _checks(file_persona: dict, live: dict) -> list[str]:
    notes: list[str] = []
    platform = str(live.get("platform") or "")
    if platform in {"Win32", "Win64"}:
        notes.append(f"FAIL platform={platform} (expected Linux)")
    else:
        notes.append(f"OK platform={platform}")

    ua = str(live.get("userAgent") or "")
    if "Chrome/151" in ua or "Chrome/151." in ua:
        notes.append("OK Chrome 151 in UA")
    else:
        notes.append(f"WARN UA is not Chrome 151: {ua[:80]}")

    renderer = str((live.get("webgl") or {}).get("renderer") or "")
    if any(token in renderer for token in ("Direct3D", "D3D11", "Segoe")):
        notes.append(f"FAIL host GPU leaked a Windows renderer: {renderer}")
    elif renderer:
        notes.append(f"OK WebGL is host-like: {renderer}")
    else:
        notes.append("WARN WebGL renderer empty")

    if "webgl_vendor" in file_persona or "font_families" in file_persona:
        notes.append("FAIL persona.json must not spoof GPU/fonts on linux-chrome")
    else:
        notes.append("OK persona.json omitted GPU/fonts")

    cores_file = file_persona.get("hardware_concurrency")
    cores_live = live.get("hardwareConcurrency")
    if cores_file is not None and cores_live == cores_file:
        notes.append(f"OK hardwareConcurrency file={cores_file} live={cores_live}")
    else:
        notes.append(
            f"WARN hardwareConcurrency file={cores_file} live={cores_live} "
            "(rebuild may not include split hardware gate)"
        )

    tz_file = file_persona.get("timezone_id")
    tz_live = live.get("timezone")
    if tz_file and tz_live == tz_file:
        notes.append(f"OK timezone file={tz_file} live={tz_live}")
    else:
        notes.append(
            f"WARN timezone file={tz_file} live={tz_live} "
            "(geoip CLI overlay / locale gate — expected after this rebuild)"
        )
    return notes


def _run_once(
    *,
    profile: Path,
    headless: bool,
    fingerprint: str,
    proxy: str | None,
    geoip: bool,
    screenshot: bool,
    wait_ms: int,
) -> tuple[dict, dict]:
    profile.mkdir(parents=True, exist_ok=True)
    print(f"Launching Hexium linux-chrome  seed={fingerprint!r}  profile={profile}", flush=True)
    browser = launch(
        headless=headless,
        humanize=True,
        show_cursor=not headless,
        fingerprint=fingerprint,
        proxy=proxy,
        geoip=geoip,
        user_data_dir=str(profile),
    )
    try:
        page = _one_tab(browser)
        page.goto("https://example.com", wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_selector("h1", timeout=15_000)
        live = page.evaluate(_READ_SIGNALS)
        if screenshot:
            ensure_artifact_dirs()
            shot = SCREENSHOTS_DIR / "linux_chrome_persona.png"
            page.screenshot(path=str(shot), full_page=True)
            print(f"Screenshot: {shot}", flush=True)
        if wait_ms > 0:
            print(f"Waiting {wait_ms / 1000:.0f}s...", flush=True)
            try:
                page.wait_for_timeout(wait_ms)
            except PlaywrightError:
                pass
    finally:
        try:
            browser.close()
        except PlaywrightError:
            pass
    file_persona = _load_persona_json(profile)
    return file_persona, live


def main() -> int:
    parser = argparse.ArgumentParser(description="linux-chrome persona example")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--proxy", default=None)
    parser.add_argument(
        "--fingerprint",
        default="hexium-linux-proof-1",
        help="Pinned seed (same seed → same screen/cores)",
    )
    parser.add_argument(
        "--no-geoip",
        action="store_true",
        help="Do not resolve timezone/locale from egress IP",
    )
    parser.add_argument(
        "--twice",
        action="store_true",
        help="Launch twice with the same seed and compare cores/screen",
    )
    parser.add_argument("--no-screenshot", action="store_true")
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=WAIT_MS,
        help="Hold the page open after the screenshot (0 to exit immediately)",
    )
    args = parser.parse_args()

    geoip = not args.no_geoip
    if args.proxy:
        geoip = True

    profile = get_profiles_root() / "linux-chrome-example"
    file_persona, live = _run_once(
        profile=profile,
        headless=not args.headed,
        fingerprint=args.fingerprint,
        proxy=args.proxy,
        geoip=geoip,
        screenshot=not args.no_screenshot,
        wait_ms=args.wait_ms,
    )

    _print_block("persona.json", file_persona)
    _print_block("live page", live)
    print("\n=== checks ===", flush=True)
    for line in _checks(file_persona, live):
        print(line, flush=True)

    if args.twice:
        print("\nSecond launch (same seed)...", flush=True)
        file2, live2 = _run_once(
            profile=profile,
            headless=not args.headed,
            fingerprint=args.fingerprint,
            proxy=args.proxy,
            geoip=geoip,
            screenshot=False,
            wait_ms=args.wait_ms,
        )
        same = (
            live.get("hardwareConcurrency") == live2.get("hardwareConcurrency")
            and (live.get("screen") or {}).get("width") == (live2.get("screen") or {}).get("width")
            and file_persona.get("seed") == file2.get("seed")
        )
        print(
            "OK same seed → same cores/screen"
            if same
            else "FAIL same seed produced different cores/screen",
            flush=True,
        )

    print("\nDone.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
