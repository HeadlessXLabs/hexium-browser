# Testing Hexium Browser (Python wrapper)

`hexium_browser.launch()` uses Hexium Chrome 151, not Playwright’s Chromium.

Resolution order (`ensure_binary()`):

1. `HEXIUM_BINARY_PATH` if set (`HEXIUM_BINARY` is an alias)
2. Default local Hexium `chrome` if that file exists
3. Cached binary under `~/.hexium`
4. `hexium-browser fetch` — API then GitHub `Hexium-{VERSION}`

Do **not** `playwright install chromium`. Install the Playwright **driver** only (it ships with `pip install hexium-browser`).

**Headed on Lingmo:** `launch(headless=False)` injects `--gtk-version=4` and `--ozone-platform=x11` so Chrome does not SIGSEGV in GTK3. Appearance Theme stays **Classic**. Do not set `GTK_THEME=Adwaita`. `HEXIUM_NO_GTK4=1` disables the GTK4 launch flags.

**Not Incognito:** `launch()` uses `launch_persistent_context` on a real-disk profile. `browser.new_page()` opens a **tab**. Bare `launch()` creates a new `hexium-session-*` under `~/.hexium/profiles`. Pin identity with `launch(profile="Work")` or `HEXIUM_USER_DATA_DIR`.

CI on Ubuntu: [docs/CI.md](docs/CI.md).

## What's in place

| Path | Purpose |
| --- | --- |
| `src/hexium_browser/` | Playwright `launch()` wrapper |
| `examples/oracle_smoke.py` | Minimal oracle probe |
| `examples/stealth_test.py` | Full stealth suite |
| `examples/open_google.py` | Headed Google tab (persistent profile) |
| `tests/` | Unit tests (mostly mocked; no binary required) |

Playwright examples only. No Selenium / Puppeteer / crawl4ai / Lambda integrations.

Unpack `Hexium-{VERSION}-linux-x64.tar.gz` to get `hexium-v{VERSION}/chrome`. Point `HEXIUM_BINARY_PATH` at that file, or run `hexium-browser fetch`.

## Visual mouse pointer (headed debug)

A standard mouse arrow follows CDP `mousemove` from humanized `page.mouse` / `page.click()`. **Not** your OS mouse. Pass `show_cursor=False` on stealth oracles.

```bash
pip install -e '.[dev,geoip]'
hexium-browser fetch

python -c "
from hexium_browser import launch
browser = launch(headless=False, humanize=True)
page = browser.new_page()
page.goto('https://example.com')
page.click('a')
browser.close()
"
```

Oracle examples:

```bash
python examples/oracle_smoke.py
python examples/oracle_smoke.py --url https://bot.sannysoft.com
python examples/stealth_test.py
```

## Unit tests

Static/mocked tests only — no engine binary required:

```bash
python -m pytest -m 'not slow'
```

## CLI (after install + binary)

```bash
hexium-browser info --quick
hexium-browser fetch
```
