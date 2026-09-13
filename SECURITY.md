# Security

Hexium Browser 0.1.0 is alpha. The Python API is [AGPL-3.0 only](LICENSE.md). The `chrome` binary has a separate [BINARY-LICENSE.md](BINARY-LICENSE.md).

## Reporting

**Do not** file security bugs as public GitHub issues.

Use [GitHub private vulnerability reporting](https://github.com/HeadlessXLabs/hexium-browser/security/advisories/new) on this repository, or email **hello@saify.me**.

Please include:

- Wrapper version (`pip show hexium-browser`) and engine version (`hexium-browser info --quick`)
- OS / arch
- Whether the issue is in the Python wrapper, the downloaded binary, or both
- A minimal reproduction (no secrets, no third-party account cookies)

You should get a reply within a few days. There is no bug bounty program.

## Scope

In scope: RCE or sandbox escapes in the wrapper’s launch path, credential/profile leakage from `~/.hexium`, supply-chain issues in this repo’s Python package.

Out of scope: “a site detected the browser”, CAPTCHA bypass, and fingerprint-oracle scores. Those are product/stealth reports — use a normal issue.
