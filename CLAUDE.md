# Hexium Browser (wrapper)

This repository is the Playwright `launch()` wrapper (`hexium_browser`). Hexium is **Playwright `launch()` → patched Chromium 151**. Python already ships. Other languages are GitHub issues, not invented APIs.

## Do not

Never JS fingerprint inject / `addInitScript` stealth. Never document overlay paths, engine patch files, or Chromium `src/` layout in public docs. Never rebuild Chromium from this repo — use GitHub Releases and `hexium-browser fetch`.

## Product facts (do not invent)

- Default personas: Linux `linux-native`; Windows `windows-native`; macOS `macos-native` (alias `mac-native`)
- Opt-in: `windows-chrome`, `linux-chrome`. **No** `macos-chrome`
- Wrong-OS `*-native` remaps to the host native. `*-chrome` is never remapped
- GeoIP locale / timezone / WebRTC IP from the **egress IP** (default on). Explicit `timezone=` / `locale=` win
- UA Chrome **151.0.7922.174**. Engine pin `151.0.7922.174.1`
- `windows-chrome` on Linux: known WebGL **−5%** pixel-vs-name tell — do not claim it is fixed
- Bare `launch()` → new `~/.hexium/profiles/hexium-session-*`. Named `profile=` is sticky
- Binary: `HEXIUM_BINARY_PATH` → `$HEXIUM_OUT/hexium-v{VERSION}/chrome` if present → `~/.hexium` → `hexium-browser fetch`. Not Playwright’s Chromium

## Pointers

- [README.md](README.md) — marketing / quickstart
- [docs/USAGE.md](docs/USAGE.md) — launch contract
- [docs/CI.md](docs/CI.md) — Ubuntu Actions + Setup Hexium
- [docs/persona/](docs/persona/) — per-preset notes
- [CONTRIBUTING.md](CONTRIBUTING.md) — pytest, bugs
