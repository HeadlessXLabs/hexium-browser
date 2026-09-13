# Usage

Hexium Browser is Playwright `launch()` → patched Chromium 151. This page is the launch contract. The README stays the quickstart.

```python
from hexium_browser import launch

browser = launch(headless=True)
page = browser.new_page()  # a tab, not Incognito
page.goto("https://example.com")
browser.close()
```

Async: `launch_async()`. Same kwargs.

Do **not** pass `executable_path` or `channel`. `browser.new_context()` is rejected. If you used Playwright `new_context()`, switch to `launch(profile="Work")` or keep calling `new_page()`.

## `launch()`

| Kwarg | Default | Notes |
| --- | --- | --- |
| `headless` | `True` | `--headless=new`. Some anti-bot sites still detect headless; run headed (Xvfb is fine). |
| `proxy` | `None` | `http://…` or `socks5://…` (string or Playwright `ProxySettings`) |
| `profile` | `None` | Named dir under `~/.hexium/profiles/<name>` |
| `user_data_dir` | `None` | Explicit Chrome user-data-dir. `HEXIUM_USER_DATA_DIR` if set. |
| `ephemeral` | `False` | Force a new `hexium-session-*` (ignored when `profile` or `user_data_dir` is set) |
| `persona` | host native | See [Personas](#personas). Also `HEXIUM_PERSONA`. |
| `fingerprint` | auto seed | Sticky machine id. `"off"` disables engine fingerprint patches. |
| `geoip` | `True` | Timezone, locale, languages, WebRTC IP from egress IP |
| `timezone` / `locale` | GeoIP | Explicit values always win over GeoIP |
| `humanize` | `True` | Bézier mouse, per-character keys, realistic scroll |
| `human_preset` | `"default"` | Or `"careful"` |
| `show_cursor` | follows `humanize` | Virtual pointer (DOM tell). Pass `False` on stealth oracles. |
| `args` | `[]` | Extra Chromium flags (deduped with stealth args) |
| `stealth_args` | `True` | Engine seed / persona flags |
| `browser_version` | engine pin | Optional `HEXIUM_VERSION` override |
| `extension_paths` | `None` | Unpacked extension dirs |

Bare `launch()` creates `~/.hexium/profiles/hexium-session-*` plus a new fingerprint. Named `profile=` reuses `persona.json`.

## Personas

`launch(persona=…)` or `HEXIUM_PERSONA`.

| Preset | Default? | What sites see |
| --- | --- | --- |
| [`linux-native`](persona/linux-native.md) | **Linux** | This Linux machine (host GPU, fonts, screen, CPU) |
| [`windows-native`](persona/windows-native.md) | **Windows** | This Windows machine |
| [`macos-native`](persona/macos-native.md) | **macOS** | This Mac. Alias `mac-native`. |
| [`linux-chrome`](persona/linux-chrome.md) | opt-in | Linux Chrome 151 UA; **host** GPU/fonts; sampled screen/CPU/RAM |
| [`windows-chrome`](persona/windows-chrome.md) | opt-in | Win32 + Chrome 151; sampled D3D11 WebGL + Segoe. Alias `windows-1080p`. |

There is **no** `macos-chrome`.

A `*-native` name that does not match this OS remaps to the host native (`windows-native` on Linux becomes `linux-native`). `windows-chrome` and `linux-chrome` are never remapped.

UA is rewritten to **Chrome 151.0.7922.174**. Desktop UA-CH `model` is empty.

On Linux, `windows-chrome` WebGL pixels can disagree with the spoofed renderer name (about −5% vs real Windows Chrome). That is a **known tell**. Do not treat it as fixed.

```python
launch()                              # host native + GeoIP
launch(persona="linux-chrome")
launch(persona="windows-chrome")
launch(fingerprint="off")
launch(persona="windows-chrome", fingerprint="account-1")
```

## GeoIP

On by default. With `pip install -e '.[geoip]'`, Hexium maps the **egress IP** (proxy exit, or the machine public IP) to timezone, locale, `navigator.languages`, and `--hexium-webrtc-ip=`.

- `geoip=False` opts out
- Explicit `timezone=` / `locale=` always win
- Without the extra, launch continues; timezone stays the sampled UTC
- Missing GeoLite2 still returns the exit IP so WebRTC does not leak LAN
- GeoIP does not re-roll the GPU

## Humanize

Default `humanize=True`. Playwright never moves the OS cursor. A standard arrow is the virtual pointer when `show_cursor` is on (it follows `humanize` unless you set it).

| Interaction | Playwright default | `humanize=True` |
| --- | --- | --- |
| Mouse | Instant teleport | Bézier, easing, slight overshoot |
| Clicks | Instant | Aim point + hold |
| Keyboard | Instant fill | Per-character timing |
| Scroll | Jump | Accelerate → cruise → decelerate |

Presets: `human_preset="default"` or `"careful"`. Paths are **not** sticky across actions. Pass `show_cursor=False` on stealth oracles.

## Profiles

Hexium is a real Chrome user-data-dir, not Incognito.

```bash
hexium-browser profiles
hexium-browser profiles new Work
hexium-browser profiles use Work
hexium-browser profiles last
```

```python
launch()                 # new hexium-session-* + new fingerprint
launch(profile="Work")   # sticky ~/.hexium/profiles/Work
```

The sampled persona sticks on a named profile until you pass a new `fingerprint=` or another `profile=`. Home is `HEXIUM_HOME` (default `~/.hexium`). Profiles never live on `/tmp` unless you set `HEXIUM_ALLOW_TMP_PROFILE`.

## Binary

Resolution order:

1. `HEXIUM_BINARY_PATH` (alias `HEXIUM_BINARY`)
2. `$HEXIUM_OUT/hexium-v{VERSION}/chrome` if it exists
3. Cache under `~/.hexium/hexium-v{VERSION}/`
4. `hexium-browser fetch` from `https://headlessx.dev/api/download`

Pin with `HEXIUM_VERSION`. First ship: **linux-x64**. Engine version: `151.0.7922.174.1`.

## Recommended anti-bot config

Hexium does not solve CAPTCHAs. Bring your own proxy.

```python
from hexium_browser import launch

browser = launch(
    proxy="socks5://user:pass@host:1080",
    geoip=True,
    headless=False,
    humanize=True,
    show_cursor=False,  # stealth oracles
    profile="Shop",     # returning visitor
)
```

Some sites challenge first-time visitors. Warm cookies on a **named** profile; a bare `launch()` never brings cookies back.
