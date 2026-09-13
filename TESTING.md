# Testing Hexium Browser (Python wrapper)

## Current status: local Hexium binary is live

`hexium_browser.launch()` already uses the overlay Chrome, not Playwright’s Chromium.

Resolution order (`ensure_binary()`):

1. `HEXIUM_BINARY_PATH` if set (`HEXIUM_BINARY` is an alias)
2. Default local Hexium `chrome` if that file exists
3. Cached binary under `~/.hexium`
4. `hexium-browser fetch` (`allow_download=True`) — API then GitHub `Hexium-{VERSION}`

Do **not** `playwright install chromium` as the browser. Install the Playwright **driver** only if missing.

**Headed on Lingmo:** `launch(headless=False)` injects `--gtk-version=4` and `--ozone-platform=x11` so Chrome does not SIGSEGV in GTK3. Appearance Theme stays **Classic** (persistent profiles also get `extensions.theme.system_theme=0`). Do not set `GTK_THEME=Adwaita`. `HEXIUM_NO_GTK4=1` disables the GTK4 launch flags.

**Not Incognito:** `launch()` uses `launch_persistent_context` on a real-disk profile. Playwright `chromium.launch()` + `new_page()` is an off-the-record CDP context and `/tmp` tmpfs looks like Incognito to BrowserScan. `browser.new_page()` opens a **tab**. Bare `launch()` creates a new `hexium-session-*` folder under `~/.hexium/profiles` plus a new fingerprint seed. Pin identity with `launch(profile="Work")` or `HEXIUM_USER_DATA_DIR`.

## What's in place (no install needed to inspect)

| Path | Purpose |
| --- | --- |
| `src/hexium_browser/` | Playwright `launch()` wrapper |
| `examples/oracle_smoke.py` | Minimal oracle probe (run after build) |
| `examples/stealth_test.py` | Full stealth suite |
| `examples/open_google.py` | Headed Google tab (persistent profile) |
| `tests/` | Unit tests (mostly mocked; no binary required) |

Playwright examples only. No Selenium / Puppeteer / crawl4ai / Lambda integrations.

Point `HEXIUM_BINARY_PATH` at Hexium `chrome`, or build into:

```text
$HEXIUM_OUT/Hexium-{platform}-{version}/chrome
```

Example: `hexium-v151.0.7922.174.1/chrome` inside `Hexium-151.0.7922.174.1-linux-x64.tar.gz`

## Visual mouse pointer (headed debug)

A standard mouse arrow follows CDP ``mousemove`` from humanized
``page.mouse`` / ``page.click()``. **Not** your OS mouse. Pass
``show_cursor=False`` on stealth oracles (DOM tell). Humanize events are
real page ``mousemove``s.

```bash
# After build + pip install:
python -c "
from hexium_browser import launch
browser = launch(headless=False, humanize=True)
page = browser.new_page()
page.goto('https://example.com')
page.click('a')   # Bézier path + virtual mouse pointer follows API moves
browser.close()
"
```


```bash
export HEXIUM_BINARY_PATH=/path/to/hexium/chrome

pip install -e ".[dev,geoip]"
playwright install chromium   # driver only — not Playwright's Chromium

python examples/oracle_smoke.py
python examples/oracle_smoke.py --url https://bot.sannysoft.com
python examples/stealth_test.py
```

Or `hexium-browser fetch` (headlessx.dev, then GitHub Releases):

```bash
hexium-browser fetch
```

## Unit tests (optional, after pip install)

Static/mocked tests only — no engine binary required:

```bash
pytest tests/test_build_args.py tests/test_config.py tests/test_profiles.py tests/test_cli_profiles.py -q
```

## CLI (after install + binary)

```bash
hexium-browser info --quick
hexium-browser fetch
```
