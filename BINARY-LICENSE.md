# Hexium Browser binary license

The **Hexium Browser** `chrome` binary is a modified Chromium build. It is **not** the Python package and it is **not** Google Chrome.

## What this file covers

This license applies to prebuilt Hexium binaries (`chrome`, `chrome.exe`, `Hexium.app`) delivered via `hexium-browser fetch`, cache under `~/.hexium/hexium-v{VERSION}/`, or a local out path:

```text
${HEXIUM_DOWNLOAD_URL}/hexium-v{VERSION}/hexium-{platform}{ext}
$HEXIUM_OUT/hexium-v{VERSION}/hexium-{platform}{ext}
```

Runnable binary after extract (same layout as `~/.hexium/hexium-v{VERSION}/`):

```text
$HEXIUM_OUT/hexium-v{VERSION}/chrome
```

Examples:

```text
hexium-v151.0.7922.174.1/hexium-linux-x64.tar.gz
hexium-v151.0.7922.174.1/chrome
hexium-v151.0.7922.174.1/hexium-linux-arm64.tar.gz
hexium-v151.0.7922.174.1/hexium-darwin-arm64.tar.gz
hexium-v151.0.7922.174.1/hexium-darwin-x64.tar.gz
hexium-v151.0.7922.174.1/hexium-windows-x64.zip
```

The Python wrapper (`hexium_browser`) is licensed separately under [AGPL-3.0 only](LICENSE.md).

## Chromium

Hexium is based on Chromium. Chromium is Copyright The Chromium Authors and is available under the BSD 3-Clause License and other notices in the Chromium source tree. See:

- https://chromium.googlesource.com/chromium/src/+/HEAD/LICENSE
- https://www.chromium.org/chromium-projects/

You must retain Chromium copyright, license, and notice files shipped with the binary.

## Not Google Chrome

Hexium Browser is **not** an official Google product. You may not use Google trademarks, the Chrome brand, or Google’s proprietary Chrome components as if this were Google Chrome. Web identity (User-Agent) matching Chrome 151 does not grant trademark rights.

## Hexium modifications

HeadlessXLabs modifications to Chromium that ship inside the Hexium binary are licensed to you solely as part of that binary, for running Hexium Browser. Redistribution of the binary must keep this `BINARY-LICENSE.md`, Chromium notices, and must not strip corresponding source obligations that Chromium’s licenses already require.

## No warranty

THE BINARY IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT.
