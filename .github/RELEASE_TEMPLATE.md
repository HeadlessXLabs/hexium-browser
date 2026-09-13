# Release template

Two release **kinds**. Attach the Chromium tarball **once** — on the engine tag only. Never re-upload it on `vX.Y.Z`.

## Engine (binary lives here)

| Field | Value |
| --- | --- |
| Tag | `Hexium-{VERSION}` |
| Title | `Hexium-{VERSION}` |
| Asset (Linux x86_64) | `Hexium-{VERSION}-linux-x64.tar.gz` |
| Checksum | `Hexium-{VERSION}-linux-x64.tar.gz.sha256` |

Asset URL:

```text
https://github.com/HeadlessXLabs/hexium-browser/releases/download/Hexium-{VERSION}/Hexium-{VERSION}-linux-x64.tar.gz
```

This ship:

```text
https://github.com/HeadlessXLabs/hexium-browser/releases/download/Hexium-151.0.7922.174.1/Hexium-151.0.7922.174.1-linux-x64.tar.gz
```

Notes:

```markdown
Hexium engine **{VERSION}** (Linux x86_64). Web identity is Chrome **{UA_VERSION}**.

Python wrapper: [Hexium_browser-{PY}](https://github.com/HeadlessXLabs/hexium-browser/releases/tag/v{PY})

Unpacks to `hexium-v{VERSION}/chrome`. Point `HEXIUM_BINARY_PATH` at that file, or run `hexium-browser fetch`.
```

```bash
gh release create "Hexium-{VERSION}" --target main --title "Hexium-{VERSION}" \
  --notes-file notes.md \
  "Hexium-{VERSION}-linux-x64.tar.gz" \
  "Hexium-{VERSION}-linux-x64.tar.gz.sha256"
```

## Python package (no binary)

| Field | Value |
| --- | --- |
| Tag | `v{X.Y.Z}` |
| Title | `Hexium_browser-{X.Y.Z}` |
| Assets | none — link the engine release |

Notes:

```markdown
Python package **hexium-browser {X.Y.Z}**.

Engine binary (already uploaded, do not attach again):
[Hexium-{VERSION}](https://github.com/HeadlessXLabs/hexium-browser/releases/tag/Hexium-{VERSION})

pip install hexium-browser
pip install 'hexium-browser[geoip]'
hexium-browser fetch
```

```bash
gh release create "v{X.Y.Z}" --target main --title "Hexium_browser-{X.Y.Z}" --notes-file notes.md
```
