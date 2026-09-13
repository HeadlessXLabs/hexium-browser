# Changelog

All notable changes to Hexium Browser — wrapper and binary — are documented here.

Changes are tagged: **[wrapper]** for the Python package, **[binary]** for Chromium patches, **[docs]** for this repo’s markdown.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning is [SemVer](https://semver.org/) while this tree is **0.1.x alpha**.

---

## [Unreleased]

### [wrapper]

- `hexium-browser fetch` extracts the engine tarball once. A loop around `tar.extractall` made CI look stuck after “Extracting to ~/.hexium/hexium-v…”.

### [docs]

- Maintainer ship checklist: [`UPDATE.md`](UPDATE.md).

---

## [0.1.1] — 2026-09-13

PyPI [`hexium-browser` 0.1.1](https://pypi.org/project/hexium-browser/0.1.1/) and Docker Hub [`saifyxpro/hexium-browser:0.1.1`](https://hub.docker.com/r/saifyxpro/hexium-browser).

### [wrapper]

- GitHub Action **Setup Hexium** (`.github/actions/setup-hexium`) caches `~/.hexium/hexium-v{VERSION}/` and runs `hexium-browser fetch` on miss. Ubuntu CI installs the package, restores the binary, runs `pytest -m 'not slow'`, and a headless `launch()` smoke.
- Publish workflows (`.github/workflows/publish-pypi.yml`, `publish-docker.yml`) on `v*` tags. They fail if PyPI or Docker Hub already has that version (no silent overwrite).
- Windows fonts: `HEXIUM_FONTS_DIR` / `~/.hexium/fonts/windows` (no machine-local default path).
- Docker image `saifyxpro/hexium-browser` — Xvfb + geoip extra + Linux Chrome 151 pre-fetched at build. linux/amd64 only.

### [docs]

- README: PyPI / pepy / Docker Hub (`saifyxpro`) badges, Docker install (`:0.1.1` / `:latest`, profile volume), hero demo as GIF.
- Setup Hexium Action + Ubuntu CI. Engine tarball only on `Hexium-{VERSION}` releases.

---

## [0.1.0] — 2026-09-13

**Alpha.** First Hexium Browser ship: Playwright `launch()` in, Google Chrome **151.0.7922.174** out. Persistent disk profiles, C++ personas, GeoIP, humanize. No JS fingerprint injectors. Python-only; [.NET](https://github.com/HeadlessXLabs/hexium-browser/issues/1), [npm](https://github.com/HeadlessXLabs/hexium-browser/issues/2), [Go](https://github.com/HeadlessXLabs/hexium-browser/issues/3), and [Rust](https://github.com/HeadlessXLabs/hexium-browser/issues/4) are tracked as What’s next.

### [binary]

- Chromium **151.0.7922.174.1** (engine product). Web identity is four-part **151.0.7922.174** (User-Agent and UA-CH `fullVersion` / brand list). Desktop UA-CH `model` is empty.
- Named persona presets:
  - **`linux-native`** — Linux default. Host GPU, fonts, screen, CPU.
  - **`windows-native`** — Windows default. Host pass-through (not a sampled D3D GPU).
  - **`macos-native`** — macOS default (alias `mac-native`). Host pass-through. No `macos-chrome`.
  - **`linux-chrome`** — Linux Chrome 151 UA; host GPU/fonts; sampled screen/CPU/RAM.
  - **`windows-chrome`** — Win32 + sampled D3D11 WebGL + Segoe pack (alias `windows-1080p`). Opt-in on Linux.
- A `*-native` name that does not match the host OS remaps to that host’s native preset.
- `--hexium-fingerprint=off` — fingerprint surface pass-through (P0 automation stealth stays on).
- Canvas LSB noise **off** unless `--hexium-noise=on`.
- GeoIP overlays (`--hexium-timezone=`, `--hexium-locale=`, `--hexium-webrtc-ip=`) apply after the named preset. Locale tags keep the region (`en-PK`); `--lang` uses a Chrome 151 language pack the binary actually ships (e.g. `en-GB` for commonwealth English).
- Windows UA-CH `platformVersion` is Chrome 151 reduced form: **10.0.0** (Win10) or **15.0.0** (Win11). Never UniversalApiContract **19.0.0**. Frozen UA still says `Windows NT 10.0` for both (stock Chrome).
- Known: Linux `windows-chrome` can show BrowserScan **WebGL exception −5%** (D3D11 name vs host pixels). Not claimed fixed. Score-max on a Linux host is `linux-native`.

### [wrapper]

- `from hexium_browser import launch` — drop-in Playwright Chromium launch. `launch_persistent_context` only (real user-data-dir, not Incognito).
- Bare `launch()` mints `~/.hexium/profiles/hexium-session-*` and a new fingerprint. `profile="Work"` / `HEXIUM_USER_DATA_DIR` / `fingerprint="account-1"` stick.
- CLI: `hexium-browser info`, `fetch`, `profiles` (`new` / `use` / `last`).
- Auto-download linux-x64 from `https://headlessx.dev/api/download`, then GitHub Releases `Hexium-{VERSION}` (pin with `HEXIUM_VERSION`). `HEXIUM_BINARY_PATH` / `$HEXIUM_OUT` win when set.
- `humanize=True` by default — Bézier mouse, per-character typing, scroll. Virtual mouse pointer follows CDP moves; pass `show_cursor=False` on stealth oracles (DOM tell).
- GeoIP **on by default** (`pip install 'hexium-browser[geoip]'`). Egress IP → timezone, `navigator.languages`, WebRTC mask IP. Explicit `timezone=` / `locale=` win. Without the extra, launch continues; timezone stays sampled UTC.
- `windows-chrome` on Linux: fontconfig jail + Segoe pack (`HEXIUM_FONTS_DIR` or engine bundle). Incomplete pack warns once (`HEXIUM_SUPPRESS_FONT_WARNING=1`). Headless WebGPU flags only for that persona.
- Sampled `linux-chrome` / `windows-chrome` write `persona.json` next to the profile; natives do not.
- SOCKS5 and HTTP(S) proxies, including `user:pass@host:port`.

### [docs]

- README quickstart, [Usage](docs/USAGE.md), [persona pages](docs/persona/README.md), CONTRIBUTING, SUPPORT, SECURITY, CLAUDE.md.
- Oracle captures (12 Sep 2026): reCAPTCHA v3 demo **0.9**, BrowserScan bot **Normal**, DABI human, sannysoft WebDriver missing.

[Unreleased]: https://github.com/HeadlessXLabs/hexium-browser/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/HeadlessXLabs/hexium-browser/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/HeadlessXLabs/hexium-browser/releases/tag/v0.1.0
