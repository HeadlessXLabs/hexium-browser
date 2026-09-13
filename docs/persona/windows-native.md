# `windows-native`

**Windows default.** Sites see **this Windows machine**: host GPU, fonts, screen, and CPU.

```python
from hexium_browser import launch

launch()                         # Windows → windows-native
launch(persona="windows-native")
```

Timezone, locale, languages, and WebRTC IP still follow **GeoIP** from the egress IP (default on). Explicit `timezone=` / `locale=` win.

UA is Chrome **151.0.7922.174**.

## Remap

`windows-native` on Linux or macOS remaps to that host’s native (`linux-native` / `macos-native`). To spoof Win32 on Linux, pass [`windows-chrome`](windows-chrome.md) (opt-in; not remapped).
