# `windows-chrome`

**Opt-in** on every OS (never remapped). Alias: `windows-1080p`.

Sites see **Win32 + Chrome 151**: sampled D3D11 WebGL / WebGPU, Segoe font pack, sampled screen/CPU/RAM. UA-CH `platformVersion` is clamped to **10.0.0** / **15.0.0** (never 19.0.0). UA is rewritten to **151.0.7922.174**. Desktop UA-CH `model` is empty.

```python
from hexium_browser import launch

launch(persona="windows-chrome")
launch(persona="windows-chrome", fingerprint="account-1")
```

## Linux host

Needs a Segoe pack: `HEXIUM_FONTS_DIR`, or the engine Windows font bundle. Without fonts, launch should refuse rather than mix Linux fonts into a Win32 UA.

**Known tell:** on Linux, WebGL **pixels** can disagree with the spoofed renderer **name** (about −5% vs real Windows Chrome). That pixel-vs-name mismatch is **not** claimed fixed. Do not treat “hash matches Windows” as a guarantee.

## GeoIP

Timezone/locale still come from the egress IP (default on). GeoIP does not re-roll the GPU. Same `fingerprint=` / named `profile=` keeps the sampled machine.
