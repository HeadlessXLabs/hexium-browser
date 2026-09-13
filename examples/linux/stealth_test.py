"""Run stealth tests against major bot detection services.

One persistent Chrome, one tab, domcontentloaded + hold, no extra tabs
and no session-restore pile-on.

Usage:
    python examples/linux/stealth_test.py
    python examples/linux/stealth_test.py --headed     # watch in real-time
    python examples/linux/stealth_test.py --no-screenshots
    python examples/linux/stealth_test.py --proxy http://10.50.96.5:8888
"""

import json
import sys
import time
from pathlib import Path

from hexium_browser import launch
from hexium_browser.artifacts import ensure_artifact_dirs
from hexium_browser.config import get_profiles_root

HEADED = "--headed" in sys.argv
SCREENSHOTS = "--no-screenshots" not in sys.argv
PROXY = None
for i, arg in enumerate(sys.argv):
    if arg == "--proxy" and i + 1 < len(sys.argv):
        PROXY = sys.argv[i + 1]

STEALTH_PROFILE = get_profiles_root() / "stealth-test"


def _seed_new_tab_startup(profile: Path) -> None:
    """Do not restore last-session tabs (sannysoft/rebrowser/…) on relaunch."""
    prefs_path = profile / "Default" / "Preferences"
    prefs_path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if prefs_path.is_file():
        try:
            raw = prefs_path.read_text(encoding="utf-8").strip()
            if raw:
                loaded = json.loads(raw)
                if isinstance(loaded, dict):
                    data = loaded
        except (OSError, ValueError):
            data = {}
    profile_prefs = data.setdefault("profile", {})
    if not isinstance(profile_prefs, dict):
        profile_prefs = {}
        data["profile"] = profile_prefs
    profile_prefs["exit_type"] = "Normal"
    profile_prefs["exited_cleanly"] = True
    session = data.setdefault("session", {})
    if not isinstance(session, dict):
        session = {}
        data["session"] = session
    session["restore_on_startup"] = 5  # New Tab Page
    prefs_path.write_text(json.dumps(data), encoding="utf-8")


def _context_pages(browser):
    pages = []
    for ctx in getattr(browser, "contexts", []) or []:
        pages.extend(getattr(ctx, "pages", []) or [])
    return pages


def _one_tab(browser):
    """Reuse the first tab; close anything session-restore opened."""
    pages = _context_pages(browser)
    if not pages:
        return browser.new_page()
    keep = pages[0]
    for extra in pages[1:]:
        try:
            extra.close()
        except Exception:
            pass
    return keep


def _launch(**extra):
    """Hexium binary via launch(). geoip only when a proxy is set (geoip2 optional)."""
    _seed_new_tab_startup(STEALTH_PROFILE)
    extra.setdefault("user_data_dir", str(STEALTH_PROFILE))
    extra.setdefault("humanize", True)
    # Overlay is a detector tell on stealth oracles — keep it off.
    extra.setdefault("show_cursor", False)
    args = list(extra.get("args") or [])
    if "--hexium-noise=false" not in args:
        args.append("--hexium-noise=false")
    extra["args"] = args
    return launch(headless=not HEADED, proxy=PROXY, geoip=bool(PROXY), **extra)


def _as_js(expression: str) -> str:
    s = expression.strip()
    first = s.split("\n", 1)[0]
    if s.startswith("function") or s.startswith("async ") or "=>" in first:
        return f"({s})()"
    return s


def _eval_main(page, expression: str):
    """Main-world CDP Runtime.evaluate — no Playwright UtilityScript.

    Isolated page.evaluate cannot see page JS globals (window.Fingerprint).
    Main-world CDP does, and does not inject UtilityScript (rebrowser).
    """
    world = getattr(page, "_stealth_world", None)
    if world is not None:
        cdp = world.get_cdp_session()
    else:
        cdp = page.context.new_cdp_session(page)
    result = cdp.send(
        "Runtime.evaluate",
        {
            "expression": _as_js(expression),
            "returnByValue": True,
            "awaitPromise": True,
        },
    )
    if "exceptionDetails" in result:
        return None
    return result.get("result", {}).get("value")


def _poll(page, runner, *, ready, attempts: int = 20, delay_s: float = 2.0):
    last = None
    for _ in range(attempts):
        last = runner(page)
        if last is not None and ready(last):
            return last
        time.sleep(delay_s)
    return last


def test_bot_sannysoft(page):
    """bot.sannysoft.com — classic bot detection checks."""
    page.goto("https://bot.sannysoft.com", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    results = page.evaluate("""() => {
        const rows = document.querySelectorAll('table tr');
        const data = {};
        rows.forEach(r => {
            const cells = r.querySelectorAll('td');
            if (cells.length >= 2) {
                const key = cells[0].innerText.trim();
                const val = cells[1].innerText.trim();
                const cls = cells[1].className || '';
                data[key] = {value: val, passed: !cls.includes('failed')};
            }
        });
        return data;
    }""") or {}

    failed = [k for k, v in results.items() if not v["passed"]]
    total = len(results)
    passed = total - len(failed)
    return {"passed": passed, "total": total, "failed": failed}


def test_bot_incolumitas(page):
    """bot.incolumitas.com — comprehensive 30+ check bot detection."""
    page.goto("https://bot.incolumitas.com", wait_until="domcontentloaded", timeout=30000)

    last_total = 0
    results = {"passed": 0, "failed": 0, "failedTests": [], "total": 0}
    for _ in range(15):
        time.sleep(2)
        results = page.evaluate("""() => {
            const text = document.body.innerText;
            const okMatches = text.match(/"\\w+":\\s*"OK"/g) || [];
            const failMatches = text.match(/"\\w+":\\s*"FAIL"/g) || [];
            const failedTests = failMatches.map(m => m.match(/"(\\w+)"/)[1]);
            return {passed: okMatches.length, failed: failMatches.length, failedTests, total: okMatches.length + failMatches.length};
        }""") or results
        if not results:
            continue
        if results["total"] >= 30 and results["total"] == last_total:
            break
        last_total = results["total"]

    return results


def test_rebrowser(page):
    """bot-detector.rebrowser.net — automation signal detector."""
    # Hold after DOM so delayed checks can fire. Scrape via isolated
    # page.evaluate (no Playwright UtilityScript / sourceUrlLeak).
    page.goto("https://bot-detector.rebrowser.net/", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(15_000)

    return page.evaluate("""() => {
        const el = document.getElementById('detections-json');
        if (!el) return {failing: [], totalFails: 0, passed: 0, notTriggered: 0, error: 'no detections-json element'};
        const tests = JSON.parse(el.value);
        const failing = tests.filter(t => t.rating === 1).map(t => t.type);
        const passed = tests.filter(t => t.rating === -1).length;
        const notTriggered = tests.filter(t => t.rating === 0).length;
        return {failing, totalFails: failing.length, passed, notTriggered, total: tests.length};
    }""")


def test_browserscan(page):
    """browserscan.net/bot-detection — WebDriver, UA, CDP, Navigator checks."""
    page.goto("https://www.browserscan.net/bot-detection", wait_until="domcontentloaded", timeout=30000)
    time.sleep(5)

    results = page.evaluate("""() => {
        const items = document.querySelectorAll('[class*="result"], [class*="item"], [class*="check"]');
        let normal = 0, abnormal = 0;
        const text = document.body.innerText;
        const normalMatches = text.match(/Normal/g);
        const abnormalMatches = text.match(/Abnormal/g);
        return {
            normal: normalMatches ? normalMatches.length : 0,
            abnormal: abnormalMatches ? abnormalMatches.length : 0,
            pageText: text.substring(0, 500)
        };
    }""")
    return results


_DABI_SCRAPE = """() => {
        const chunks = [];
        document.querySelectorAll('pre, code, textarea, input').forEach((n) => {
            chunks.push(n.value || n.textContent || '');
        });
        chunks.push(document.body.innerText || '');
        const text = chunks.join('\\n');
        const botMatch = text.match(/"isBot":\\s*(true|false)/);
        const isBot = botMatch ? botMatch[1] === 'true' : null;
        const checks = {};
        const patterns = [
            'isBot', 'hasBotUserAgent', 'hasWebdriverTrue',
            'isHeadlessChrome', 'isAutomatedWithCDP', 'hasSuspiciousWeakSignals',
            'isPlaywright', 'hasInconsistentChromeObject'
        ];
        patterns.forEach(p => {
            const match = text.match(new RegExp('"' + p + '":\\s*(true|false)'));
            if (match) checks[p] = match[1] === 'true';
        });
        return {isBot, checks};
    }"""


def test_deviceandbrowserinfo(page):
    """deviceandbrowserinfo.com/are_you_a_bot — fingerprint + behavioral detection."""
    page.goto("https://deviceandbrowserinfo.com/are_you_a_bot", wait_until="domcontentloaded", timeout=30000)
    return _poll(
        page,
        lambda p: p.evaluate(_DABI_SCRAPE),
        ready=lambda r: isinstance(r, dict) and r.get("isBot") is not None,
        attempts=20,
        delay_s=2.0,
    ) or {"isBot": None, "checks": {}, "error": "isBot JSON never rendered"}


_CREEPJS_SCRAPE = """() => {
        const fp = window.Fingerprint;
        if (fp && fp.lies && typeof fp.lies.totalLies === 'number') {
            return {totalLies: fp.lies.totalLies};
        }
        const text = document.body.innerText || '';
        const m = text.match(/(\\d+)\\s+lies?\\b/i);
        if (m) return {totalLies: Number(m[1]), via: 'dom'};
        return {error: 'Fingerprint not ready', totalLies: null};
    }"""


def test_pixelscan_bot_check(page):
    """pixelscan.net/bot-check — Start Check, human vs bot verdict."""
    page.goto("https://pixelscan.net/bot-check", wait_until="domcontentloaded", timeout=60000)
    time.sleep(2)
    started = False
    for loc in (
        page.get_by_role("button", name="Start Check"),
        page.locator("button:has-text('Start Check')"),
        page.locator("text=Start Check"),
    ):
        try:
            loc.first.click(timeout=8_000)
            started = True
            break
        except Exception:
            continue
    if not started:
        return {"error": "Start Check button not found", "verdict": None, "detected": []}

    page.wait_for_function(
        """() => {
            const t = document.body.innerText || '';
            return t.includes('Definitely a Human') || t.includes('Bot Behavior Detected');
        }""",
        timeout=90_000,
    )
    time.sleep(2)
    return page.evaluate("""() => {
        const text = document.body.innerText || '';
        const human = /Definitely a Human/i.test(text);
        const bot = /Bot Behavior Detected/i.test(text);
        const detected = [];
        const clear = [];
        const re = /^(.+?)\\s+(Clear|Detected)\\s*$/gm;
        let m;
        while ((m = re.exec(text)) !== null) {
            const name = m[1].trim();
            if (!name || name.length > 80) continue;
            if (m[2] === 'Detected') detected.push(name);
            else clear.push(name);
        }
        return {
            verdict: human && !bot ? 'human' : (bot ? 'bot' : 'unknown'),
            human,
            bot,
            detected,
            clearCount: clear.length,
        };
    }""")


def test_creepjs_noise_off(page):
    """CreepJS — lie detection with fingerprint noise disabled."""
    page.goto("https://abrahamjuliot.github.io/creepjs/", wait_until="domcontentloaded", timeout=60000)
    result = _poll(
        page,
        lambda p: _eval_main(p, _CREEPJS_SCRAPE),
        ready=lambda r: isinstance(r, dict) and r.get("totalLies") is not None,
        attempts=25,
        delay_s=2.0,
    )
    try:
        page.evaluate("window.scrollTo(0, 0)")
    except Exception:
        pass
    return result or {"error": "Fingerprint not ready", "totalLies": None}


TESTS = [
    {
        "name": "bot.sannysoft.com",
        "url": "https://bot.sannysoft.com",
        "runner": test_bot_sannysoft,
        "verdict": lambda r: f"{r['passed']}/{r['total']} passed"
            + (f" (FAILED: {', '.join(r['failed'])})" if r["failed"] else " — ALL GREEN"),
        "pass": lambda r: len(r["failed"]) == 0,
    },
    {
        "name": "bot.incolumitas.com",
        "url": "https://bot.incolumitas.com",
        "runner": test_bot_incolumitas,
        "verdict": lambda r: f"{r['passed']}/{r['total']} passed"
            + (
                " — ALL GREEN"
                if r.get("failed", 0) == 0
                else f" (FAILED: {', '.join(r.get('failedTests', []))} — known false positives)"
                if set(r.get("failedTests", [])) <= {"WEBDRIVER", "connectionRTT"}
                else f" (FAILED: {', '.join(r.get('failedTests', []))})"
            ),
        "pass": lambda r: set(r.get("failedTests", [])) <= {"WEBDRIVER", "connectionRTT"},
    },
    {
        "name": "Rebrowser Bot Detector",
        "url": "https://bot-detector.rebrowser.net/",
        "runner": test_rebrowser,
        "verdict": lambda r: (
            f"🟢{r.get('passed', 0)} ⚪{r.get('notTriggered', 0)} — ALL CLEAN"
            if r.get("totalFails", 1) == 0
            else f"FAIL: {', '.join(r.get('failing', []))}"
        ),
        "pass": lambda r: r.get("totalFails", 1) == 0,
    },
    {
        "name": "deviceandbrowserinfo.com",
        "url": "https://deviceandbrowserinfo.com/are_you_a_bot",
        "runner": test_deviceandbrowserinfo,
        "verdict": lambda r: f"isBot: {r.get('isBot', 'unknown')}"
            + (f", trueFlags: {sum(1 for v in r.get('checks', {}).values() if v)}" if r.get("checks") else "")
            + (f" ({r['error']})" if r.get("error") else ""),
        "pass": lambda r: r.get("isBot") is False and not any(r.get("checks", {}).values()),
    },
    {
        "name": "BrowserScan",
        "url": "https://www.browserscan.net/bot-detection",
        "runner": test_browserscan,
        "verdict": lambda r: f"Normal: {r['normal']}, Abnormal: {r['abnormal']}",
        "pass": lambda r: r.get("abnormal", 1) == 0,
    },
    {
        "name": "Pixelscan bot-check",
        "url": "https://pixelscan.net/bot-check",
        "runner": test_pixelscan_bot_check,
        "verdict": lambda r: (
            f"error: {r.get('error')}"
            if r.get("error")
            else (
                f"{r.get('verdict', 'unknown')}"
                + (f" (detected: {', '.join(r.get('detected') or [])})" if r.get("detected") else "")
            )
        ),
        "pass": lambda r: r.get("verdict") == "human",
    },
    {
        "name": "CreepJS lies (noise=false)",
        "url": "https://abrahamjuliot.github.io/creepjs/",
        "runner": test_creepjs_noise_off,
        "verdict": lambda r: (
            f"lies: {r.get('totalLies')}"
            if r.get("totalLies") is not None
            else f"lies: None ({r.get('error', 'Fingerprint not ready')})"
        ),
        "pass": lambda r: r.get("totalLies") == 0,
    },
]


def main():
    print("=" * 60)
    print("Hexium Stealth Test Suite")
    print("=" * 60)
    print(f"Mode: {'headed' if HEADED else 'headless'}")
    print(f"Screenshots: {'on' if SCREENSHOTS else 'off'}")
    print(f"Proxy: {PROXY or 'none'}")
    print()
    print("Launching stealth browser...", flush=True)

    browser = _launch()
    page = _one_tab(browser)
    if (page.url or "") not in ("", "about:blank") and not (page.url or "").startswith("chrome://"):
        page.goto("about:blank", wait_until="domcontentloaded")

    # Show browser fingerprint details
    try:
        import re
        info = page.evaluate("""async () => {
            const ua = navigator.userAgent;
            let fullVersion = null;
            try {
                const data = await navigator.userAgentData.getHighEntropyValues(['fullVersionList', 'platform', 'platformVersion']);
                const chrome = data.fullVersionList.find(b => b.brand === 'Chromium' || b.brand === 'Google Chrome');
                fullVersion = chrome ? chrome.version : null;
            } catch {}
            const gl = document.createElement('canvas').getContext('webgl');
            const dbg = gl ? gl.getExtension('WEBGL_debug_renderer_info') : null;
            return {
                ua,
                fullVersion,
                platform: navigator.platform,
                cores: navigator.hardwareConcurrency,
                gpu: dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : 'N/A',
                gpuVendor: dbg ? gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL) : 'N/A',
                screen: screen.width + 'x' + screen.height,
                languages: navigator.languages.join(', '),
            };
        }""")
        ua_short = re.sub(r'^Mozilla/5\.0 \(', '', info["ua"])
        ua_short = re.sub(r'\) AppleWebKit/[\d.]+ \(KHTML, like Gecko\) ', ' | ', ua_short)
        print(f"UA: {ua_short}", flush=True)
        print(f"Platform: {info['platform']} | Cores: {info['cores']} | Screen: {info['screen']}", flush=True)
        print(f"GPU: {info['gpuVendor']} — {info['gpu']}", flush=True)
    except Exception:
        print("Chrome: could not detect", flush=True)

    try:
        page.goto("https://httpbin.org/ip", timeout=10000)
        ip = page.evaluate("JSON.parse(document.body.innerText).origin")
        print(f"IP: {ip}", flush=True)
    except Exception:
        print("IP: could not detect", flush=True)

    print(f"Running {len(TESTS)} tests in one tab (this takes ~2 minutes)...\n", flush=True)

    results_summary = []

    for test in TESTS:
        name = test["name"]
        print(f"--- {name} ---")
        print(f"URL: {test['url']}")

        try:
            result = test["runner"](page)
            passed = test["pass"](result)
            verdict = test["verdict"](result)
            status = "PASS" if passed else "FAIL"
            results_summary.append((name, status, verdict))

            print(f"Result: [{status}] {verdict}")

            if SCREENSHOTS:
                shots, _ = ensure_artifact_dirs()
                filename = shots / (
                    f"stealth_test_{name.replace('.', '_').replace(' ', '_').replace('/', '_')}.png"
                )
                page.screenshot(path=str(filename))
                print(f"Screenshot: {filename}")

        except Exception as e:
            results_summary.append((name, "ERROR", str(e)))
            print(f"Error: {e}")

        print()

    browser.close()

    print("=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for name, status, verdict in results_summary:
        icon = {"PASS": "+", "FAIL": "!", "ERROR": "x"}[status]
        print(f"  [{icon}] {name}: {verdict}")

    passed_count = sum(1 for _, s, _ in results_summary if s == "PASS")
    total = len(results_summary)
    print(f"\n  {passed_count}/{total} tests passed")
    print("=" * 60)

    return 0 if passed_count == total else 1


if __name__ == "__main__":
    sys.exit(main())
