# Ship checklist

Two products. Two GitHub releases. Changelog first.

| Kind | Git tag | Release title | Asset |
| --- | --- | --- | --- |
| Engine | `Hexium-{VERSION}` | `Hexium-{VERSION}` | `Hexium-{VERSION}-linux-x64.tar.gz` + `.sha256` **once** |
| Wrapper | `v{X.Y.Z}` | `Hexium_browser-{X.Y.Z}` | **none** — never re-attach the tarball |

PyPI / Docker Hub refuse the same version twice. Bump `__version__` if 0.1.1 is already live.

Work on `develop`. Do not push `main` unless you mean to.

Full field copy: [`.github/RELEASE_TEMPLATE.md`](.github/RELEASE_TEMPLATE.md).

---

## 0. Changelog (always)

Edit [`CHANGELOG.md`](CHANGELOG.md) **before** tagging.

1. Move bullets from `## [Unreleased]` into a new `## [{X.Y.Z}] — YYYY-MM-DD` (wrapper) and/or `### [binary]` (engine).
2. Keep `[wrapper]` / `[binary]` / `[docs]` tags.
3. Leave `## [Unreleased]` empty (or only WIP).
4. Bottom compare links:

```markdown
[Unreleased]: https://github.com/HeadlessXLabs/hexium-browser/compare/v{X.Y.Z}...HEAD
[{X.Y.Z}]: https://github.com/HeadlessXLabs/hexium-browser/compare/v{OLD}...v{X.Y.Z}
```

If this ship is **engine-only**, still add a `### [binary]` block under Unreleased or the next wrapper version so fetch pins stay honest.

---

## 1. Engine binary (`HEXIUM_OUT` → GitHub Release)

Linux x86_64 only this alpha. Tree must look like fetch expects:

```text
$HEXIUM_OUT/hexium-v{VERSION}/chrome
```

Example: `{VERSION}` = `151.0.7922.174.1` → `hexium-v151.0.7922.174.1/chrome`.

Pack **that directory** (not a random zip of `out/`):

```bash
VERSION=151.0.7922.174.1          # engine product (five-part)
UA_VERSION=151.0.7922.174         # Chrome web identity (four-part)
: "${HEXIUM_OUT:?set HEXIUM_OUT to the engine out root}"

test -x "$HEXIUM_OUT/hexium-v${VERSION}/chrome"

# Write archives next to the repo, not into git
cd /tmp
tar -C "$HEXIUM_OUT" -czf "Hexium-${VERSION}-linux-x64.tar.gz" "hexium-v${VERSION}"
sha256sum "Hexium-${VERSION}-linux-x64.tar.gz" | tee "Hexium-${VERSION}-linux-x64.tar.gz.sha256"
```

Pin the wrapper to this engine (same PR as changelog):

- [`src/hexium_browser/config.py`](src/hexium_browser/config.py) — `CHROMIUM_VERSION` and `PLATFORM_CHROMIUM_VERSIONS`
- UA string if Chrome identity moved — [`src/hexium_browser/persona/schema.py`](src/hexium_browser/persona/schema.py) `CHROME_UA_VERSION`
- README / `docs/USAGE.md` pins that still name the old `Hexium-…` tag

Release (tarball **only** on this tag):

```bash
gh release create "Hexium-${VERSION}" \
  --repo HeadlessXLabs/hexium-browser \
  --target develop \
  --title "Hexium-${VERSION}" \
  --notes "Hexium engine **${VERSION}** (Linux x86_64). Web identity is Chrome **${UA_VERSION}**.

Unpacks to \`hexium-v${VERSION}/chrome\`. \`hexium-browser fetch\` or \`HEXIUM_BINARY_PATH\`.

Do not attach this archive to Python \`v*\` tags." \
  "/tmp/Hexium-${VERSION}-linux-x64.tar.gz" \
  "/tmp/Hexium-${VERSION}-linux-x64.tar.gz.sha256"
```

`Hexium-*` tags do **not** run PyPI/Docker publish.

---

## 2. Wrapper (Python + Docker)

Bump **once**; PyPI will reject a re-upload.

| File | What |
| --- | --- |
| [`src/hexium_browser/_version.py`](src/hexium_browser/_version.py) | `__version__ = "{X.Y.Z}"` (Hatch reads this) |
| [`CHANGELOG.md`](CHANGELOG.md) | section `## [{X.Y.Z}]` |
| README git install line | `@v{X.Y.Z}` |

Commit on `develop`, push, wait for CI.

GitHub release **without** assets:

```bash
X=0.1.2
VERSION=151.0.7922.174.1   # current engine pin

gh release create "v${X}" \
  --repo HeadlessXLabs/hexium-browser \
  --target develop \
  --title "Hexium_browser-${X}" \
  --notes "Python package **hexium-browser ${X}**.

Engine binary (already uploaded, do not attach again):
https://github.com/HeadlessXLabs/hexium-browser/releases/tag/Hexium-${VERSION}

pip install hexium-browser
pip install 'hexium-browser[geoip]'
hexium-browser fetch"
```

Pushing tag `v{X.Y.Z}` runs:

- [`.github/workflows/publish-pypi.yml`](.github/workflows/publish-pypi.yml)
- [`.github/workflows/publish-docker.yml`](.github/workflows/publish-docker.yml)

They fail if PyPI or `saifyxpro/hexium-browser:{X.Y.Z}` already exists. Tag must match `_version.py`.

Secrets: `PYPI_API_TOKEN`, `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`.

---

## Do not

- Re-upload `Hexium-{VERSION}-linux-x64.tar.gz` on `v*` / `Hexium_browser-*`
- Re-use a PyPI or Docker version that already shipped
- Commit `Hexium-*.tar.gz` (gitignored)
- Point `HEXIUM_OUT` at a path that is not `hexium-v{VERSION}/chrome`
- Pack the whole Chromium `src/` tree
