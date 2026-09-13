# Support

Hexium Browser is Playwright `launch()` → patched Chromium 151. The Python wrapper lives in this repo.

## Bugs and detection reports

Open a GitHub issue (bug template if you have it). Include:

- OS and arch
- `pip show hexium-browser` and `hexium-browser info --quick`
- `persona=` / `HEXIUM_PERSONA` (default is host native: `linux-native`, `windows-native`, or `macos-native`)
- Headed or headless
- Proxy or not (do not paste credentials)
- What you expected vs what happened

Usage reference: [docs/USAGE.md](docs/USAGE.md). Personas: [docs/persona/](docs/persona/).

## What we will not debug here

- Engine Chromium rebuilds — this repo ships the wrapper; use GitHub Releases / `hexium-browser fetch`
- CAPTCHA solving — Hexium does not solve CAPTCHAs
- Security vulnerabilities — [SECURITY.md](SECURITY.md)

There is no chat SLA. Python is the shipped wrapper; other languages are tracked as [open issues](https://github.com/HeadlessXLabs/hexium-browser/issues).
