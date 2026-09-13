# `linux-chrome`

**Opt-in.** Not the Linux default (that is [`linux-native`](linux-native.md)).

Sites see **Linux Chrome 151**: Linux UA, **host** GPU and fonts (`chrome://gpu` / WebGL stay this machine), sampled screen, CPU, and RAM from a seeded desktop row.

```python
from hexium_browser import launch

launch(persona="linux-chrome")
launch(persona="linux-chrome", fingerprint="account-1")  # same sample next time
```

Same seed → same screen/hardware. Bare `launch()` without `profile=` still mints a new seed. GeoIP timezone/locale apply even though GPU is native.

UA is Chrome **151.0.7922.174**. Desktop UA-CH `model` is empty.

This preset is **not** remapped away on Linux. There is no `macos-chrome`. For Win32 + D3D, see [`windows-chrome`](windows-chrome.md).
