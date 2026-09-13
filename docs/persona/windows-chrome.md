# `windows-chrome`

**Opt-in** on every OS (never remapped). Alias: `windows-1080p`.

Sites see **Win32 + Chrome 151**: sampled D3D11 WebGL / WebGPU, Segoe font pack, sampled screen/CPU/RAM. UA-CH `platformVersion` is clamped to **10.0.0** / **15.0.0** (never 19.0.0). UA is rewritten to **151.0.7922.174**. Desktop UA-CH `model` is empty.

```python
from hexium_browser import launch

launch(persona="windows-chrome")
launch(persona="windows-chrome", fingerprint="account-1")
```

## Linux host

Needs a Segoe pack. The wrapper ships `persona/data/fonts/windows`. Override with `HEXIUM_FONTS_DIR` if you keep fonts elsewhere. Without fonts, launch refuses rather than mix Linux fonts into a Win32 UA.

**Known tell:** on Linux, WebGL **pixels** can disagree with the spoofed renderer **name** (about −5% vs real Windows Chrome). That pixel-vs-name mismatch is **not** claimed fixed. Do not treat “hash matches Windows” as a guarantee.

**Linux host vs anti-bot:** `linux-native` matches this machine. `windows-chrome` still claims **Win32** (UA, UA-CH, D3D11 name, Segoe) while TLS, GPU pixels, and the window stack stay Linux. Sites that correlate JS OS with the network path can challenge the Win32 persona and allow the same IP as `linux-native`. That is expected for this alpha; it is not a GeoIP timeout or a missing humanize path. Real Windows is `windows-native` on a Windows build — there is no Windows Hexium binary yet.

## Headless captures

13 Sep 2026, `examples/windows-chrome/test_headless.py` on a Linux host. Screenshots, not a guarantee.

| ![Win32 headless — Vercel 0.00](../../assets/screenshots/test_headless_win_vercel.png) | ![Win32 headless — Infosimples](../../assets/screenshots/test_headless_win_infosimples.png) |
| --- | --- |
| [headless-detector.vercel.app](https://headless-detector.vercel.app/) — **0.00**, Normal Browser | [Infosimples](https://infosimples.github.io/detect-headless/) — Time Elapse pass |

## GeoIP

Timezone/locale still come from the egress IP (default on). GeoIP does not re-roll the GPU. Same `fingerprint=` / named `profile=` keeps the sampled machine.
