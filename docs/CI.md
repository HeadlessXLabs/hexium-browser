# CI

GitHub Actions on Ubuntu installs the Python package, restores the Hexium Chrome binary from cache, and runs tests. Playwright’s Chromium is never installed.

## This repository

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) on `main` / `develop`:

1. `pip install -e '.[dev,geoip]'`
2. [Setup Hexium](../.github/actions/setup-hexium/action.yml) — cache `~/.hexium/hexium-v{VERSION}/` only (named profiles are not cached)
3. `pytest -m 'not slow'`
4. Headless `launch()` to `about:blank`

Cache key: `hexium-{VERSION}-{OS}-{linux-x64|linux-arm64}`. Miss → `hexium-browser fetch` (headlessx.dev API, then GitHub Releases `Hexium-{VERSION}`).

## Use the Action in another workflow

Install `hexium-browser` first so `hexium-browser fetch` exists.

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
- run: pip install 'hexium-browser[geoip]'
- uses: HeadlessXLabs/hexium-browser/.github/actions/setup-hexium@main
  with:
    version: "151.0.7922.174.1"   # optional pin
    download-url: ""              # optional HEXIUM_DOWNLOAD_URL
- run: hexium-browser info --quick
```

Inputs match issue [#5](https://github.com/HeadlessXLabs/hexium-browser/issues/5): `version`, `download-url`. The Action sets `HEXIUM_BINARY_PATH` and `HEXIUM_VERSION`.
