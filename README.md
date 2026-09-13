<p align="center">
  <img src="assets/banners/hexium-banner.png" alt="Hexium Browser — Launch like Chrome. Stay undetected." width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Latest_Version-0.1.0-026AFD?style=for-the-badge" alt="Latest Version 0.1.0">
  <img src="https://img.shields.io/badge/Chromium-151.0.7922.174.1-4285F4?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Chromium 151.0.7922.174.1">
  <img src="https://img.shields.io/badge/python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/Playwright-only-2EAD33?style=for-the-badge&logo=playwright&logoColor=white" alt="Playwright">
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-AGPL--3.0-A32D2D?style=for-the-badge" alt="AGPL-3.0"></a>
</p>

**Launch like Chrome. Stay undetected.**

Playwright in. Chrome 151 out. Built by HeadlessX Labs.

Sites see **Google Chrome 151**. You see Hexium Browser — a C++ persona compiled into Chromium, persistent disk profiles, humanize, and GeoIP locale. No JS injectors.

<p align="center">
  <video src="assets/recordings/google_search_human_headless_new_profile.webm" width="800" controls playsinline muted></video>
  <br><em>Headless Google search, new profile — <code>examples/google_search_human_headless_new_profile.py</code></em>
</p>

## Features

- Playwright `launch()` — headed and `--headless=new`
- Linux x86_64 binary in this alpha (Windows and macOS not supported yet)
- Persistent disk profiles (real tabs, not Incognito)
- C++ persona presets — Linux default `linux-native`; see [Personas](#personas)
- Seeded fingerprint sample (`fingerprint=` or auto `--hexium-seed=`) — not a new GPU every page
- Humanized mouse, keys, and scroll (`humanize=True`)
- GeoIP timezone, locale, and WebRTC IP from the egress IP (on by default)
- Chrome 151 web identity (User-Agent and related surface)

Depth lives in [docs/](#docs). This README is the quickstart.

## Launch

```python
from hexium_browser import launch

browser = launch(headless=True)  # new ~/.hexium/profiles/hexium-session-* + new fingerprint
browser = launch(
    profile="Work",
    headless=True,
    proxy="http://user:pass@host:port",
    humanize=True,
    fingerprint="account-1",
)  # sticky ~/.hexium/profiles/Work
```

`browser.new_page()` opens a **tab**. Bare `launch()` is a new visitor each time; use `profile="Work"` or `HEXIUM_USER_DATA_DIR` to return to the same identity.

```bash
python examples/linux_chrome_persona.py
python examples/windows_chrome_persona.py --headed
python examples/stealth_test.py
python examples/open_google.py
```

## Install

```bash
pip install hexium-browser
pip install 'hexium-browser[geoip]'   # timezone / locale / WebRTC from egress IP
hexium-browser fetch                  # Chrome 151 binary (Linux x86_64)
```

From this repo (if PyPI is not what you want):

```bash
pip install 'hexium-browser[geoip] @ git+https://github.com/HeadlessXLabs/hexium-browser.git@v0.1.0'
hexium-browser fetch
```

Requires Python 3.9+ and the Playwright **driver** (ships with the `playwright` package). Do **not** `playwright install chromium` — Hexium launches its own Chrome 151 binary.

GeoIP is on by default; without the extra, launch continues and timezone stays the sampled UTC.

## CLI

```bash
hexium-browser fetch          # download the engine (API, then GitHub Releases)
hexium-browser install        # alias for fetch
hexium-browser info           # wrapper + binary diagnostics
hexium-browser info --quick   # skip launching chrome --version
hexium-browser info --json
hexium-browser info --proxy socks5://user:pass@host:1080
hexium-browser doctor         # alias for info
hexium-browser clear-cache    # delete ~/.hexium cached binaries
hexium-browser profiles       # list named profiles
hexium-browser profiles list
hexium-browser profiles new Work
hexium-browser profiles use Work
hexium-browser profiles last
```

## Profiles

Hexium is a real Chrome user-data-dir, not Incognito. Bare `launch()` creates a new `~/.hexium/profiles/hexium-session-*` and a new fingerprint. Named profiles stick. `profiles use` only records the last name for the CLI; `launch()` still needs `profile="Work"` (or `HEXIUM_USER_DATA_DIR`) to reopen it.

```python
from hexium_browser import launch
launch()  # new identity
launch(profile="Work")  # returning visitor
```

The sampled persona sticks on a named profile until you pass a new `fingerprint=` or use another `profile=`.

**Migrating from Playwright?** One-line change:

```diff
- from playwright.sync_api import sync_playwright
- pw = sync_playwright().start()
- browser = pw.chromium.launch()
+ from hexium_browser import launch
+ browser = launch()

page = browser.new_page()
page.goto("https://example.com")
# ... rest of your code works unchanged
```

`page.goto()`, `click()`, `fill()`, `locator()`, and `browser.close()` are the same Playwright objects. Do **not** pass `executable_path` or `channel`. `browser.new_page()` is a **tab** on a persistent disk profile (not Incognito). If you used `browser.new_context()`, switch to `launch(profile="Work")` or keep calling `new_page()`.

## Why Hexium Browser?

- **JS stealth injectors break** — they patch `navigator` in page JS. Detection sites look for the patch. Hexium does not inject stealth scripts.
- **Persona is compiled in** — GPU, screen, UA, and hardware reporting follow a sampled Chrome persona at the C++ layer, plus a persistent profile on disk.
- **Same Playwright API** — `launch()`, `new_page()`, `click()`, `fill()`. Swap the import.
- **Humanize is a flag** — Bézier mouse, per-character typing, realistic scroll. A virtual mouse pointer is on whenever `humanize` is on; pass `show_cursor=False` for stealth oracles.

Hexium does not solve CAPTCHAs. Bring your own proxy. Use the Playwright API you already know.

## Test results

Captured 12 Sep 2026 against live oracles with Chrome 151 (`examples/stealth_test.py`, `examples/recaptcha_score.py`, `examples/fingerprint_scan_test.py`). These are screenshots, not a guarantee that every site will score the same.

| Oracle | What the capture shows |
| --- | --- |
| reCAPTCHA v3 demo | score **0.9** |
| BrowserScan bot detection | **Normal** |
| deviceandbrowserinfo.com | **You are human!** (`isBot: false`) |
| bot.sannysoft.com | WebDriver missing, `window.chrome` present, plugins **5**, UA Chrome/151 |
| Rebrowser bot detector | no webdriver / no `__pwInitScripts` (some checks need a click to fire) |

| ![reCAPTCHA v3 demo — score 0.9](assets/screenshots/recaptcha_score.png) | ![BrowserScan — Normal](assets/screenshots/stealth_test_BrowserScan.png) |
| --- | --- |
| reCAPTCHA v3 demo — score 0.9 | BrowserScan bot detection — Normal |

| ![deviceandbrowserinfo.com — You are human!](assets/screenshots/stealth_test_deviceandbrowserinfo_com.png) | ![bot.sannysoft.com — WebDriver passed](assets/screenshots/stealth_test_bot_sannysoft_com.png) |
| --- | --- |
| deviceandbrowserinfo.com — “You are human!” | bot.sannysoft.com — WebDriver missing, Chrome present, plugins 5 |

| ![Rebrowser bot detector](assets/screenshots/stealth_test_Rebrowser_Bot_Detector.png) | ![bot.incolumitas.com](assets/screenshots/stealth_test_bot_incolumitas_com.png) |
| --- | --- |
| Rebrowser bot detector — no webdriver, no Playwright init scripts | bot.incolumitas.com — `examples/stealth_test.py` |

<details>
<summary>CreepJS</summary>

| ![CreepJS lies, noise=false](assets/screenshots/stealth_test_CreepJS_lies_%28noise=false%29.png) | ![CreepJS](assets/screenshots/creepjs.png) |
| --- | --- |
| CreepJS (noise=false) — `examples/stealth_test.py` | CreepJS — `examples/fingerprint_scan_test.py` |

</details>

<details>
<summary>fingerprint-scan.com</summary>

<p align="center">
<img src="assets/screenshots/fingerprint-scan.png" width="600" alt="fingerprint-scan.com">
<br><em>fingerprint-scan.com — <code>examples/fingerprint_scan_test.py</code></em>
</p>

</details>

Stealth/oracle examples pass `humanize=True` and **`show_cursor=False`**. The virtual pointer is a DOM tell. `launch()` turns it **on** whenever `humanize` is on; pass `False` to hide it.

## Humanize

`launch()` defaults to `humanize=True`, and `show_cursor` follows that. Playwright never moves the OS cursor — a standard mouse arrow is the virtual pointer.

```python
from hexium_browser import launch

browser = launch(headless=False, humanize=True)
page = browser.new_page()
page.goto("https://example.com")
page.locator("#email").fill("user@example.com")
page.locator("button[type=submit]").click()
```

| Interaction | Playwright default | `humanize=True` |
| --- | --- | --- |
| Mouse | Instant teleport | Bézier curve, easing, slight overshoot |
| Clicks | Instant | Aim point + hold |
| Keyboard | Instant fill | Per-character timing |
| Scroll | Jump | Accelerate → cruise → decelerate |

| [Humanize click demo](assets/recordings/humanize_click_demo.webm) | Still |
| --- | --- |
| ![Humanize click demo](assets/screenshots/humanize_click_demo.png) | Same demo — virtual highlighter mid-path |

| [Headed Google search](assets/recordings/google_search_human.webm) | Still |
| --- | --- |
| ![Google search results after humanize](assets/screenshots/google_search_human.png) | After the headed search — “Nextjs Latest version” |

| [DABI interaction oracle](assets/recordings/dabi_interactions_mouse.webm) | Still |
| --- | --- |
| ![DABI interaction oracle](assets/screenshots/dabi_interactions_mouse.png) | Same interaction run — still frame |

| Headless, reused profile | Headless, fresh profile |
| --- | --- |
| ![Headless Google search still](assets/screenshots/google_search_human_headless.png) | ![Headless Google search, new profile](assets/screenshots/google_search_human_headless_new_profile.png) |

## Personas

`launch(persona=…)` or `HEXIUM_PERSONA`. Linux default is **`linux-native`**. Windows default is **`windows-native`**. macOS default is **`macos-native`** (alias `mac-native`). Pass `windows-chrome` or `linux-chrome` to sample. A `*-native` name that does not match this OS remaps to the host native. The engine binary alone uses the same host defaults.

| Preset | What sites see | GPU / fonts | When |
| --- | --- | --- | --- |
| **[`linux-native`](docs/persona/linux-native.md)** | This machine | Host GPU, fonts, screen, CPU | **Linux default.** |
| **[`windows-native`](docs/persona/windows-native.md)** | This Windows machine | Host GPU, fonts, screen, CPU | **Windows default.** |
| **[`macos-native`](docs/persona/macos-native.md)** | This macOS machine | Host GPU/fonts | **macOS default.** Alias `mac-native`. No `macos-chrome`. |
| **[`linux-chrome`](docs/persona/linux-chrome.md)** | Linux Chrome 151 | **Host** GPU and fonts; screen/CPU/RAM still sampled | `persona="linux-chrome"` |
| **[`windows-chrome`](docs/persona/windows-chrome.md)** | Win32 + Chrome 151 | Sampled D3D11 WebGL + Segoe pack. On Linux: known WebGL −5% pixel-vs-name tell (not claimed fixed). | `persona="windows-chrome"` (alias `windows-1080p`) |

```python
from hexium_browser import launch

launch()                              # Linux: linux-native + GeoIP tz/lang
launch(persona="linux-chrome")        # Linux UA, real GPU, sampled screen
launch(persona="windows-chrome")      # Win32 UA + D3D + Segoe pack
launch(fingerprint="off")             # fingerprint patches off
launch(persona="windows-chrome", fingerprint="account-1")  # same machine next time
```

Windows-on-Linux needs a Segoe pack (`HEXIUM_FONTS_DIR`, or the engine Windows font bundle). Desktop UA-CH `model` is **empty** (stock Chrome 151). Do not cartesian OS×GPU — one OS + one joint sample.

```bash
python examples/linux_chrome_persona.py
python examples/windows_chrome_persona.py --headed
```

### What is random vs sticky

A **fingerprint seed** picks one coherent device. Same seed → same machine. Bare `launch()` mints a new seed (and a new `hexium-session-*`). `profile="Work"` or `fingerprint="account-1"` reuses `persona.json`.

| Surface | Source | Sticky with seed? |
| --- | --- | --- |
| Screen (width/height/avail/DPR) | Joint Chrome desktop sample | Yes |
| `hardwareConcurrency`, `deviceMemory` | Same sample (Windows desktop min 4 GB) | Yes |
| WebGL vendor/renderer, WebGPU vendor/arch | Same sample (`windows-chrome` only) | Yes |
| UA-CH `platformVersion` (Win10 vs Win11) | Same sample; clamped to **10.0.0** / **15.0.0** (never 19.0.0); UA rewritten to **151.0.7922.174** | Yes |
| Fonts | Fixed Windows pack on `windows-chrome`; host on linux-* | Yes (not shuffled per page) |
| Timezone, locale, `navigator.languages`, WebRTC IP | **GeoIP** from egress IP (default on) | Follows the proxy/IP, not the seed |
| Canvas LSB noise | **Off** unless `args=["--hexium-noise=on"]` | Seed-stable if you turn it on |
| Mouse / keys / scroll | `humanize=True` (default) | **No** — new path each action (`human_preset="default"` or `"careful"`) |

GeoIP does not re-roll the GPU. Explicit `timezone=` / `locale=` always win over GeoIP.

<p align="center">
<img src="assets/screenshots/linux_chrome_persona.png" width="600" alt="linux-chrome persona on example.com">
<br><em>linux-chrome persona on example.com (<code>examples/linux_chrome_persona.py</code>)</em>
</p>

## Binary

**Linux x86_64 only** for this alpha. Windows and macOS are not supported yet — we are actively working on them. Thanks for your patience.

Archives are named **Hexium + engine version + OS + arch**:

```text
Hexium-{VERSION}-{os}-{arch}.tar.gz
```

This ship:

```text
Hexium-151.0.7922.174.1-linux-x64.tar.gz
```

Unpack it and you get `hexium-v151.0.7922.174.1/chrome` (same layout as `~/.hexium/hexium-v{VERSION}/`). Point `HEXIUM_BINARY_PATH` at that `chrome`, or run `hexium-browser fetch`.

The tarball is attached **once**, on the engine release — not on Python `vX.Y.Z` tags:

- Engine + binary: [Hexium-151.0.7922.174.1](https://github.com/HeadlessXLabs/hexium-browser/releases/tag/Hexium-151.0.7922.174.1)
- Python package notes: [Hexium_browser-0.1.0](https://github.com/HeadlessXLabs/hexium-browser/releases/tag/v0.1.0)

`hexium-browser fetch` tries `https://headlessx.dev/api/download` first. On 404 it downloads:

```text
https://github.com/HeadlessXLabs/hexium-browser/releases/download/Hexium-{VERSION}/Hexium-{VERSION}-linux-x64.tar.gz
```

If that version is gone, fetch takes the newest GitHub tag named `Hexium-*` (never the Python `v0.1.0` tag).

Resolution order:

1. `HEXIUM_BINARY_PATH` (alias `HEXIUM_BINARY`)
2. `$HEXIUM_OUT/hexium-v{VERSION}/chrome` if it exists
3. Cache under `~/.hexium/hexium-v{VERSION}/`
4. `hexium-browser fetch` — headlessx.dev API, then GitHub Releases `Hexium-{VERSION}`

Pin the engine with `HEXIUM_VERSION`.

| Env | Job |
| --- | --- |
| `HEXIUM_DOWNLOAD_URL` | Primary download prefix (default `https://headlessx.dev/api/download`) |
| `HEXIUM_VERSION` | Engine version (`151.0.7922.174.1`) |
| `HEXIUM_BINARY_PATH` | Exact `chrome` path |
| `HEXIUM_OUT` | Local out root |
| `HEXIUM_CACHE_DIR` | Cache root (`~/.hexium`) |
| `HEXIUM_GITHUB_REPO` | Releases repo (default `HeadlessXLabs/hexium-browser`) |

```bash
hexium-browser fetch
hexium-browser info --quick
```

## GeoIP

GeoIP is **on by default**. With `hexium-browser[geoip]`, Hexium maps the **egress IP** (proxy exit, or the machine public IP when there is no proxy) to timezone, locale, languages, and `--hexium-webrtc-ip=`. Pass `geoip=False` to opt out. Explicit `timezone=` / `locale=` always win. Without the extra, launch continues and timezone stays the sampled UTC. Missing GeoLite2 still returns the exit IP so WebRTC does not leak LAN.

## Docs

| Doc | What |
| --- | --- |
| [Changelog](CHANGELOG.md) | 0.1.0 alpha and later |
| [Usage](docs/USAGE.md) | `launch()`, personas, GeoIP, humanize, profiles |
| [CI](docs/CI.md) | Ubuntu Actions, Setup Hexium, pytest |
| [Personas](docs/persona/README.md) | `linux-native`, `linux-chrome`, `windows-native`, `windows-chrome`, `macos-native` |
| [Contributing](CONTRIBUTING.md) | Install, pytest, bug reports |
| [Support](SUPPORT.md) | How to file issues |
| [Security](SECURITY.md) | Vulnerability reports |
| [CLAUDE.md](CLAUDE.md) | Agent / contributor product rules |

Persona notes: [linux-native](docs/persona/linux-native.md) · [linux-chrome](docs/persona/linux-chrome.md) · [windows-native](docs/persona/windows-native.md) · [windows-chrome](docs/persona/windows-chrome.md) · [macos-native](docs/persona/macos-native.md)

## Troubleshooting

### Still getting blocked on aggressive sites (DataDome, Turnstile)?

Some sites detect `--headless=new` even with the C++ persona. Run **headed** on a virtual display when you have no monitor:

```bash
# Install Xvfb (virtual framebuffer)
sudo apt install xvfb

# Start virtual display
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
```

```python
from hexium_browser import launch

# Headed Chrome + residential proxy
browser = launch(headless=False, proxy="http://your-residential-proxy:port")
page = browser.new_page()
page.goto("https://example.com")
browser.close()
```

That is a real headed window on Xvfb — no physical monitor. Combine with the config below. Pass `show_cursor=False` on stealth oracles (the highlighter is a DOM tell). Hexium does not solve CAPTCHAs.

### Recommended config for anti-bot sites

Most blocks come from missing one of these three things, not from browser fingerprint detection:

```python
from hexium_browser import launch

browser = launch(
    proxy="http://your-residential-proxy:port",  # residential IP — datacenter IPs get blocked by reputation alone
    geoip=True,      # default; timezone + locale follow the proxy exit IP
    headless=False,  # headed — some sites still detect --headless=new
    humanize=True,   # default; mouse, keys, scroll
)
```

`geoip=True` needs `pip install 'hexium-browser[geoip]'`. Without the extra, launch still works and timezone stays the sampled UTC.

If the proxy supports SOCKS5, prefer it — SOCKS5 tunnels raw TCP and avoids HTTP CONNECT issues some proxies have with HTTP/2:

```python
browser = launch(
    proxy="socks5://user:pass@proxy:1080",
    geoip=True,
    headless=False,
    humanize=True,
)
```

Linux default persona is `linux-native`. Windows default is `windows-native`. macOS default is `macos-native`. `windows-chrome` needs a Segoe pack (`HEXIUM_FONTS_DIR`, or the engine Windows font bundle). Named `profile=` keeps the same fingerprint; a bare `launch()` is a new visitor each time.

### Sites challenge fresh sessions but work after first visit

Some sites challenge first-time visitors with no cookies over HTTP/2. That is a Chromium / site behavior, not a Hexium-only tell. Warm cookies once on a **named profile**, then reuse it:

```python
from hexium_browser import launch

# First run: warm up with --disable-http2
browser = launch(profile="Shop", args=["--disable-http2"])
page = browser.new_page()
page.goto("https://example.com")  # writes cookies into ~/.hexium/profiles/Shop
browser.close()

# Later runs — same profile, no --disable-http2
browser = launch(profile="Shop")
page = browser.new_page()
page.goto("https://example.com")  # returning visitor
browser.close()
```

A bare `launch()` is a new `hexium-session-*` every time, so cookies never come back. Pin `profile=` (or `user_data_dir=`) when you need a returning visitor.

For a one-shot session, `launch(args=["--disable-http2"])` forces HTTP/1.1. Only use that flag on sites that need it — most are fine on HTTP/2. SOCKS5 (`proxy="socks5://user:pass@host:port"`) avoids HTTP CONNECT entirely.

## What's next

Python `hexium_browser` already ships ([PyPI](https://pypi.org/project/hexium-browser/)). First-party packages still to land (thin bindings over the same `launch()` contract — not a new fingerprint stack):

- [.NET / NuGet](https://github.com/HeadlessXLabs/hexium-browser/issues/1)
- [npm](https://github.com/HeadlessXLabs/hexium-browser/issues/2)
- [Go](https://github.com/HeadlessXLabs/hexium-browser/issues/3)
- [Rust crate](https://github.com/HeadlessXLabs/hexium-browser/issues/4)
- [Java/JVM bindings](https://github.com/HeadlessXLabs/hexium-browser/issues/6) if demand appears

## License

- **Python API** — [GNU Affero GPL v3.0 only](LICENSE.md) (not “or later”)
- **`chrome` binary** — [BINARY-LICENSE.md](BINARY-LICENSE.md) (Chromium notices + Hexium build)

Last reviewed: 13 Sep 2026

