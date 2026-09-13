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
docker build -t saifyxpro/hexium-browser .
```

## Publish (PyPI + Docker)

Do **not** run these on every push. They fire on `v*` tags (`v0.1.1`) or **workflow_dispatch**.

| Workflow | File |
| --- | --- |
| PyPI | [`.github/workflows/publish-pypi.yml`](../.github/workflows/publish-pypi.yml) |
| Docker Hub | [`.github/workflows/publish-docker.yml`](../.github/workflows/publish-docker.yml) |

Both **fail** if that version is already published (PyPI JSON 200, or Docker Hub tag 200). They do not overwrite `hexium-browser==0.1.0` or `saifyxpro/hexium-browser:0.1.1`. `latest` is only pushed after a **new** version tag check passes. Git tags must match `src/hexium_browser/_version.py`.

Secrets / GitHub Environment:

| Name | Used by |
| --- | --- |
| GitHub Environment `pypi` | Trusted publishing (OIDC) and/or `PYPI_API_TOKEN` |
| `PYPI_API_TOKEN` | PyPI (optional if Trusted Publisher is set) |
| `DOCKERHUB_USERNAME` | Docker Hub |
| `DOCKERHUB_TOKEN` | Docker Hub access token |

Engine tarball tags (`Hexium-151…`) do **not** trigger these workflows.
