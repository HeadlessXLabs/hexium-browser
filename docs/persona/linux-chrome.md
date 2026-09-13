# `linux-chrome`

**Opt-in.** Not the Linux default (that is [`linux-native`](linux-native.md)).

Sites see **Linux x86_64 + Chrome 151**: Linux UA / UA-CH, sampled screen, CPU, and RAM from a seeded desktop row. GPU/WebGL (`chrome://gpu`) and fonts stay **this machine** — the wrapper records WebGL/fonts on the sample for diagnostics, then omits them from engine `persona.json`. `use_native_surfaces` stays true, so Blink does not spoof Mesa/ANGLE or jail fontconfig. That is unlike [`windows-chrome`](windows-chrome.md) (sampled D3D11 + Segoe).

```python
from hexium_browser import launch

launch(persona="linux-chrome")
launch(persona="linux-chrome", fingerprint="account-1")  # same sample next time
```

Same seed → same screen/hardware. Bare `launch()` without `profile=` still mints a new seed. GeoIP timezone/locale still apply.

UA is Chrome **151.0.7922.174**. Desktop UA-CH `model` is empty.

This preset is **not** remapped away on Linux. There is no `macos-chrome`. For Win32 + D3D, see [`windows-chrome`](windows-chrome.md).
