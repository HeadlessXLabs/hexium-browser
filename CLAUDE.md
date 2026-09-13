# Hexium Browser (wrapper)

This repository is the Playwright `launch()` wrapper (`hexium_browser`). Hexium is **Playwright `launch()` → patched Chromium 151**. Python already ships. Other languages are GitHub issues, not invented APIs.

## Do not run

Never run `autoninja`, `gn gen`, `gclient sync`, `apply-overlay.sh`, or `precompile-hexium.sh`. Print a rebuild command; the **user** runs it. Never JS fingerprint inject / `addInitScript` stealth. Never document overlay paths, engine patch files, or Chromium `src/` layout in public docs.

Maintainers rebuild with:

```bash
source ~/.bashrc
cd "${CHROMIUM_SRC}"
gn gen "${HEXIUM_OUT}" --args="$(cat ${HEXIUM_DEVELOP}/engine/gn/hexium_args.gn)"
autoninja -C "${HEXIUM_OUT}" chrome
```

## Product facts (do not invent)

- Default personas: Linux `linux-native`; Windows `windows-native`; macOS `macos-native` (alias `mac-native`)
- Opt-in: `windows-chrome`, `linux-chrome`. **No** `macos-chrome`
- Wrong-OS `*-native` remaps to the host native. `*-chrome` is never remapped
- GeoIP locale / timezone / WebRTC IP from the **egress IP** (default on). Explicit `timezone=` / `locale=` win
- UA Chrome **151.0.7922.174**. Engine pin `151.0.7922.174.1`
- `windows-chrome` on Linux: known WebGL **−5%** pixel-vs-name tell — do not claim it is fixed
- Bare `launch()` → new `~/.hexium/profiles/hexium-session-*`. Named `profile=` is sticky
- Binary: `HEXIUM_BINARY_PATH` → `$HEXIUM_OUT/hexium-v{VERSION}/chrome` → `~/.hexium` → `hexium-browser fetch`. Not Playwright’s Chromium

## Pointers

- [README.md](README.md) — marketing / quickstart
- [docs/USAGE.md](docs/USAGE.md) — launch contract
- [docs/persona/](docs/persona/) — per-preset notes
- [CONTRIBUTING.md](CONTRIBUTING.md) — pytest, bugs
