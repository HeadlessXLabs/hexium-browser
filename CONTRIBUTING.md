# Contributing

This repo is the **Python** Playwright wrapper: `from hexium_browser import launch`. Hexium is patched Chromium 151. Do not invent APIs, JS fingerprint injectors, or a second stealth stack.

## Install the wrapper

Python 3.9+. Use a venv. The package is not on PyPI yet.

```bash
python -m pip install -e '.[dev,geoip]'
```

That installs Playwright’s **driver**. Do **not** `playwright install chromium` as the browser — `launch()` uses Hexium’s own Chrome 151 binary (`HEXIUM_BINARY_PATH`, `$HEXIUM_OUT/hexium-v{VERSION}/chrome`, `~/.hexium`, or `hexium-browser fetch`).

```bash
hexium-browser info --quick
```

## Tests

Unit tests are mocked. They do not need a live engine binary.

```bash
python -m pytest -m 'not slow'
```

`@pytest.mark.slow` hits a real browser or live oracles. Run those only when you have Hexium `chrome` and intend to.

Examples:

```bash
python examples/linux_chrome_persona.py
python examples/windows_chrome_persona.py --headed
python examples/stealth_test.py
```

Stealth/oracle scripts should pass `humanize=True` and `show_cursor=False` (the virtual pointer is a DOM tell).

## Bugs

Open a GitHub issue with OS, `hexium_browser` version (`pip show hexium-browser`), persona, headed vs headless, and whether a proxy was used. See [SUPPORT.md](SUPPORT.md). Security reports go to [SECURITY.md](SECURITY.md), not a public issue.

## Engine rebuild (maintainers only)

Wrapper changes do not require a Chromium rebuild. If the **engine** binary must be rebuilt, **you** run it on a plugged-in machine. Agents must never run `autoninja`, `gn gen`, `gclient sync`, or `precompile-hexium.sh`.

```bash
source ~/.bashrc
cd "${CHROMIUM_SRC}"
gn gen "${HEXIUM_OUT}" --args="$(cat ${HEXIUM_DEVELOP}/engine/gn/hexium_args.gn)"
autoninja -C "${HEXIUM_OUT}" chrome
```

Do not ask an agent to execute that block.

## Pull requests

Keep diffs focused. Match existing `launch()` / persona behavior (see [docs/USAGE.md](docs/USAGE.md) and [CLAUDE.md](CLAUDE.md)). Do not add `macos-chrome`. Do not promise the Linux `windows-chrome` WebGL pixel-vs-name tell is fixed. User-facing changes go in [CHANGELOG.md](CHANGELOG.md) under **Unreleased** until the next tag.
