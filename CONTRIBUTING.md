# Contributing

This repo is the **Python** Playwright wrapper: `from hexium_browser import launch`. Hexium is patched Chromium 151. Do not invent APIs, JS fingerprint injectors, or a second stealth stack.

## Install the wrapper

Python 3.9+. Use a venv.

```bash
pip install 'hexium-browser[geoip]'
hexium-browser fetch
```

From a clone (pytest, docs edits):

```bash
python -m pip install -e '.[dev,geoip]'
hexium-browser fetch
hexium-browser info --quick
```

That installs Playwright’s **driver**. Do **not** `playwright install chromium` — `launch()` uses Hexium’s Chrome 151 (`HEXIUM_BINARY_PATH`, `~/.hexium/hexium-v{VERSION}/`, or `hexium-browser fetch`).

CI: [docs/CI.md](docs/CI.md).

## Tests

Unit tests are mocked. They do not need a live engine binary.

```bash
python -m pytest -m 'not slow'
```

`@pytest.mark.slow` hits a real browser or live oracles. Run those only when you have Hexium `chrome` and intend to.

Examples:

```bash
python examples/linux-chrome/linux_chrome_persona.py
python examples/windows-chrome/windows_chrome_persona.py --headed
python examples/linux-native/stealth_test.py
```

Stealth/oracle scripts should pass `humanize=True` and `show_cursor=False` (the virtual pointer is a DOM tell).

## Bugs

Open a GitHub issue with OS, `hexium_browser` version (`pip show hexium-browser`), persona, headed vs headless, and whether a proxy was used. See [SUPPORT.md](SUPPORT.md). Security reports go to [SECURITY.md](SECURITY.md), not a public issue.

## Engine binary

This wrapper does not rebuild Chromium. Maintainers publish `Hexium-{VERSION}-linux-x64.tar.gz` on GitHub Releases. Everyone else runs `hexium-browser fetch` or sets `HEXIUM_BINARY_PATH`.

## Pull requests

Keep diffs focused. Match existing `launch()` / persona behavior (see [docs/USAGE.md](docs/USAGE.md) and [CLAUDE.md](CLAUDE.md)). Do not add `macos-chrome`. Do not promise the Linux `windows-chrome` WebGL pixel-vs-name tell is fixed. User-facing changes go in [CHANGELOG.md](CHANGELOG.md) under **Unreleased** until the next tag.
