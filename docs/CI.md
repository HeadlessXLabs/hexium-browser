# CI

GitHub Actions on Ubuntu installs the Python package, restores the Hexium Chrome binary from cache, and runs tests. Playwright’s Chromium is never installed.

## This repository

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) on `main` / `develop`:

1. `pip install -e '.[dev,geoip]'`
2. [Setup Hexium](../.github/actions/setup-hexium/action.yml) — cache `~/.hexium/hexium-v{VERSION}/` only (named profiles are not cached)
3. `pytest -m 'not slow'`
4. Headless `launch()` to `about:blank`

On miss, `hexium-browser fetch` uses GitHub Releases first in Actions (the API host is fallback). Any failed URL, including connection reset, tries the next.

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

Local image:

```bash
docker build -t headlessxlabs/hexium-browser .
```
