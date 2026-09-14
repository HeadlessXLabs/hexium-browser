# Usage

Hexium Browser is Playwright `launch()` → patched Chromium 151. This page is the launch contract. The README stays the quickstart. GitHub Actions: [CI](CI.md).

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
| `proxy` | `None` | `http://…` or `socks5://…` (string or Playwright `ProxySettings`). See [Proxy](#proxy). |
| `profile` | `None` | Named dir under `~/.hexium/profiles/<name>` — **sticky** cookies + fingerprint |
| `user_data_dir` | `None` | Explicit Chrome user-data-dir. `HEXIUM_USER_DATA_DIR` if set. |
| `ephemeral` | `False` | New `hexium-session-*` + resampled persona (ignored when `profile` or `user_data_dir` is set) |
| `persona` | host native | See [Personas](#personas). Also `HEXIUM_PERSONA`. |
| `fingerprint` | auto seed | Sticky machine id. `"off"` disables engine fingerprint patches. |
| `geoip` | `True` | Timezone, locale, languages, WebRTC IP from egress IP |
| `timezone` / `locale` | GeoIP | Explicit values always win over GeoIP |
| `humanize` | `True` | Bézier mouse, per-character keys, realistic scroll |
| `human_preset` | `"default"` | Or `"careful"` |
| `show_cursor` | `False` | Optional blue debug ring (`humanize_click_demo.py`). Keep off on real sites. |
| `args` | `[]` | Extra Chromium flags (deduped with stealth args) |
| `stealth_args` | `True` | Engine seed / persona flags |
| `allow_3p_cookies` | `False` | Opt-in `--hexium-allow-3p-cookies`. Also `HEXIUM_ALLOW_3P_COOKIES=1`. Default **off**. |
| `browser_version` | engine pin | Optional `HEXIUM_VERSION` override |
| `extension_paths` | `None` | Unpacked extension dirs |

Bare `launch()` creates `~/.hexium/profiles/hexium-session-*` plus a new fingerprint. Named `profile=` reuses `persona.json`.

## Proxy

Hexium does not provide proxies. Pass your own via `proxy=` or, in the repo examples, `HEXIUM_PROXY` (read in Python — not a built-in env var the wrapper auto-loads). **Never put real proxy credentials in docs, git, or issue reports** — use placeholders such as `USER`, `PASS`, `host`, `port`.

```python
# HTTP(S) — typical for residential providers
launch(proxy="http://USER:PASS@host:port")

# SOCKS5 — only if your provider actually offers SOCKS on that endpoint
launch(proxy="socks5://USER:PASS@host:port")

# Playwright dict (same as above; useful when creds have special characters)
launch(proxy={"server": "http://host:port", "username": "USER", "password": "PASS"})
```

**Scheme:** include `http://` or `socks5://`. A bare `user:pass@host:port` string (no scheme) is treated as **HTTP**.

**Credentialed proxies:** stock Chromium cannot put `user:pass@` in `--proxy-server` for HTTP. Hexium’s published 151 Linux binary **does** parse inline HTTP credentials. Default wrapper behavior still uses Playwright’s proxy dict (username/password) so HTTP 407 works without extra env. Opt in to inline Chromium auth with:

- `HEXIUM_HTTP_PROXY_INLINE_AUTH=1` — inline HTTP creds in `--proxy-server`
- `HEXIUM_SOCKS_PROXY_INLINE_AUTH=1` — inline SOCKS5 creds in `--proxy-server` (native SOCKS UDP ASSOCIATE is not this engine)

SOCKS5 **without** credentials still uses `--proxy-server=socks5://host:port`.

Every `proxy=` launch also tells the engine it is a proxied session (including Playwright’s proxy dict, which does not set `--proxy-server`), and applies `--disable-http2`, `--disable-quic`, and `--force-webrtc-ip-handling-policy=disable_non_proxied_udp`.

**GeoIP + proxy:** with `pip install 'hexium-browser[geoip]'`, timezone/locale/WebRTC follow the **proxy exit IP**. Lookup waits **30s** by default (`HEXIUM_GEOIP_TIMEOUT_SECONDS` to override). GeoIP sets `--hexium-webrtc-ip=` and `HEXIUM_WEBRTC_MASK_IP` to that exit IP so child processes see the same mask.

**WebRTC:** the published Hexium 151 binary rewrites ICE candidate addresses so SDP / `localDescription` follow the GeoIP/mask IP (`HEXIUM_WEBRTC_MASK_IP` / `--hexium-webrtc-ip=`). `linux-native` does not mask unless that exit IP is set. HTTP CONNECT cannot carry STUN UDP, so a rotating pool can still show two **proxy** exits. Point `HEXIUM_BINARY_PATH` at the matching `chrome` from `hexium-browser fetch` (see [Binary](#binary)).

**Rotating proxy (new browser identity each run)** — do **not** use a named profile. For shops, prefer **headed `linux-native` + ephemeral + HTTP proxy**:

```python
launch(
    proxy="http://USER:PASS@host:port",
    persona="linux-native",
    ephemeral=True,
    geoip=True,
    headless=False,
    humanize=True,
)
# Avoid: profile="Shop", fingerprint="account-1", HEXIUM_USER_DATA_DIR=...
```

Each run gets a new `hexium-session-*` dir and a new random `--hexium-seed`. That is **not** the same as proxy IP rotation — exit IP is controlled by your provider’s username/zone (sticky session ids in the proxy user string pin the IP; omit them for rotate pools).

**Warm sticky session (cookies + same fingerprint)** — use a named profile:

```python
launch(proxy="http://USER:PASS@host:port", profile="Shop", geoip=True)
```

**Repo examples** (set `HEXIUM_PROXY` yourself; never commit real creds):

| Script | Persona | Notes |
| --- | --- | --- |
| [`examples/linux-native/allegro_pl_headed_http_proxy_ephemeral_random_profile.py`](../examples/linux-native/allegro_pl_headed_http_proxy_ephemeral_random_profile.py) | `linux-native` | **Recommended shop pattern:** headed + HTTP proxy + ephemeral random profile |
| [`examples/windows-chrome/allegro_pl_headed_windows_chrome_http_proxy_ephemeral_random_profile.py`](../examples/windows-chrome/allegro_pl_headed_windows_chrome_http_proxy_ephemeral_random_profile.py) | `windows-chrome` | Same flow with sampled Win32 (known WebGL tell on Linux — not the shop default) |
| [`examples/windows-chrome/win-google-http-proxy.py`](../examples/windows-chrome/win-google-http-proxy.py) | `windows-chrome` | Minimal Google + proxy smoke |
| [`examples/windows-chrome/browserscan-http-proxy-with-profile.py`](../examples/windows-chrome/browserscan-http-proxy-with-profile.py) | `windows-chrome` | Headed BrowserScan + HTTP proxy + **named** profile (`HEXIUM_PROFILE`, default `BrowserScan`). Use a sticky proxy session. |
| [`examples/linux-native/whoer_headed_http_proxy_ephemeral_random_profile.py`](../examples/linux-native/whoer_headed_http_proxy_ephemeral_random_profile.py) | `linux-native` | Headed [whoer.net](https://whoer.net/) + rotating HTTP proxy + ephemeral profile (20s then screenshot) |
| [`examples/windows-chrome/whoer_headed_http_proxy_ephemeral_random_profile.py`](../examples/windows-chrome/whoer_headed_http_proxy_ephemeral_random_profile.py) | `windows-chrome` | Same whoer flow |
| [`examples/linux-chrome/whoer_headed_http_proxy_ephemeral_random_profile.py`](../examples/linux-chrome/whoer_headed_http_proxy_ephemeral_random_profile.py) | `linux-chrome` | Same whoer flow |

Shared launch kwargs: [`examples/allegro_common.py`](../examples/allegro_common.py) (Allegro) and [`examples/whoer_common.py`](../examples/whoer_common.py) (whoer). Both use `ephemeral=True`, `geoip=True`, `humanize=True`, proxy from `HEXIUM_PROXY`.

```bash
export HEXIUM_BINARY_PATH=/path/to/hexium-v151.0.7922.174.1/chrome   # from fetch, or HEXIUM_BINARY_PATH
export HEXIUM_PROXY='http://USER:PASS@host:port'                     # placeholders only — never real creds
export HEXIUM_GEOIP_TIMEOUT_SECONDS=30
python examples/linux-native/allegro_pl_headed_http_proxy_ephemeral_random_profile.py
```

## Personas

`launch(persona=…)` or `HEXIUM_PERSONA`.

| Preset | Default? | What sites see |
| --- | --- | --- |
| [`linux-native`](persona/linux-native.md) | **Linux** | This Linux machine (host GPU, fonts, screen, CPU). **Shop default.** |
| [`windows-native`](persona/windows-native.md) | **Windows** | This Windows machine |
| [`macos-native`](persona/macos-native.md) | **macOS** | This Mac. Alias `mac-native`. |
| [`linux-chrome`](persona/linux-chrome.md) | opt-in | Linux x86_64 + Chrome 151; sampled screen/CPU/RAM. GPU/WebGL and fonts stay host. |
| [`windows-chrome`](persona/windows-chrome.md) | opt-in | Win32 + Chrome 151; sampled D3D11 WebGL + Segoe. Alias `windows-1080p`. |

There is **no** `macos-chrome`.

A `*-native` name that does not match this OS remaps to the host native (`windows-native` on Linux becomes `linux-native`). `windows-chrome` and `linux-chrome` are never remapped.

UA is rewritten to **Chrome 151.0.7922.174**. Desktop UA-CH `model` is empty.

On Linux, `windows-chrome` WebGL pixels can disagree with the spoofed renderer name (about −5% vs real Windows Chrome). That is a **known tell**. The same residential IP can pass as `linux-native` and get challenged as `windows-chrome` because JS still claims Win32. Do not treat it as fixed. Prefer `linux-native` for shops on Linux.

```python
launch()                              # host native + GeoIP
launch(persona="linux-chrome")
launch(persona="windows-chrome")
launch(fingerprint="off")
launch(persona="windows-chrome", fingerprint="account-1")
```

## GeoIP

On by default. With `pip install 'hexium-browser[geoip]'`, Hexium maps the **egress IP** (proxy exit, or the machine public IP) to timezone, locale, `navigator.languages`, `--hexium-webrtc-ip=`, `HEXIUM_WEBRTC_MASK_IP`, and the process `TZ` (so `Date.toString()` matches `Intl`, not the host).

- `geoip=False` opts out
- Explicit `timezone=` / `locale=` always win
- Without the extra, launch continues; timezone stays the sampled UTC
- Missing GeoLite2 still returns the exit IP so WebRTC does not leak LAN
- GeoIP does not re-roll the GPU
- Lookup waits **30s** by default (`HEXIUM_GEOIP_TIMEOUT_SECONDS` to override)

## Humanize

Default `humanize=True`. Playwright never moves the OS cursor. Each `page.mouse.move()` / `page.click()` / `fill()` runs a Bézier path, aim-and-hold click, per-character typing, and accelerated scroll.

`show_cursor` defaults to **`False`**. Humanize does not need a DOM overlay. Pass `show_cursor=True` only in headed debug demos ([`humanize_click_demo.py`](../examples/linux-native/humanize_click_demo.py)) to see the blue Camoufox-style ring. Real sites (Allegro, shops): leave it off.

| Interaction | Playwright default | `humanize=True` |
| --- | --- | --- |
| Mouse | Instant teleport | Bézier, easing, slight overshoot |
| Clicks | Instant | Aim point + hold |
| Keyboard | Instant fill | Per-character timing |
| Scroll | Jump | Accelerate → cruise → decelerate |

Presets: `human_preset="default"` or `"careful"`. Paths are **not** sticky across actions.

## Profiles

Hexium is a real Chrome user-data-dir, not Incognito.

```bash
hexium-browser profiles
hexium-browser profiles list
hexium-browser profiles new Work
hexium-browser profiles use Work
hexium-browser profiles last
```

```python
launch()                      # new hexium-session-* + new random seed
launch(ephemeral=True)        # same effect when no profile= (explicit in examples)
launch(profile="Work")        # sticky ~/.hexium/profiles/Work
```

| Mode | Cookies | Fingerprint seed | Use when |
| --- | --- | --- | --- |
| `launch()` / `ephemeral=True` | Fresh each run | New random seed | Rotating proxy tests, one-shot shop visits |
| `launch(profile="Work")` | Persist | Reused from `persona.json` | Warm logins, returning shopper |

The sampled persona sticks on a named profile until you pass a new `fingerprint=` or another `profile=`. Do not set `HEXIUM_USER_DATA_DIR` if you want a fresh session each run. Home is `HEXIUM_HOME` (default `~/.hexium`). Profiles never live on `/tmp` unless you set `HEXIUM_ALLOW_TMP_PROFILE`.

## Binary

Sites see Chrome **151.0.7922.174**. The matching Hexium engine is **151.0.7922.174.1** (Linux x86_64). Point `HEXIUM_BINARY_PATH` at that `chrome`, or run `hexium-browser fetch`. This published binary includes HTTP inline proxy auth and WebRTC ICE rewrite to the GeoIP/mask IP.

Resolution order:

1. `HEXIUM_BINARY_PATH` (alias `HEXIUM_BINARY`) — exact `chrome` path
2. `$HEXIUM_OUT/hexium-v{VERSION}/chrome` if it exists
3. Cache under `~/.hexium/hexium-v{VERSION}/`
4. `hexium-browser fetch` — `https://headlessx.dev/api/download`, then GitHub
   `https://github.com/HeadlessXLabs/hexium-browser/releases/download/Hexium-{VERSION}/Hexium-{VERSION}-linux-x64.tar.gz`
   (latest `Hexium-*` tag if that version 404s). The tarball is only on engine releases, not Python `vX.Y.Z`.

Pin with `HEXIUM_VERSION`. First ship: **linux-x64**. Engine version: `151.0.7922.174.1`.

```bash
pip install hexium-browser
pip install 'hexium-browser[geoip]'
hexium-browser fetch
hexium-browser info --quick

# Optional: pin the unpacked chrome
export HEXIUM_BINARY_PATH="$HOME/.hexium/hexium-v151.0.7922.174.1/chrome"
```

## Recommended anti-bot config

Hexium does not solve CAPTCHAs. Bring your own proxy. See [Proxy](#proxy) for HTTP vs SOCKS5 and credentialed-proxy behavior.

**Shops (recommended):** headed **`linux-native`**, ephemeral session, HTTP proxy placeholders — not `windows-chrome`:

```python
from hexium_browser import launch

browser = launch(
    proxy="http://USER:PASS@host:port",
    persona="linux-native",
    ephemeral=True,
    geoip=True,
    headless=False,
    humanize=True,
)
```

**Warm returning visitor** (sticky cookies + fingerprint):

```python
browser = launch(
    proxy="http://USER:PASS@host:port",
    persona="linux-native",
    geoip=True,
    headless=False,
    humanize=True,
    profile="Shop",
)
```

Some sites challenge first-time visitors. Warm cookies on a **named** profile; `ephemeral=True` without `profile=` never brings cookies back.
