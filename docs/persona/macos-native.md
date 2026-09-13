# `macos-native`

**macOS default.** Alias: `mac-native`. Sites see **this Mac**: host GPU, fonts, screen, and CPU.

```python
from hexium_browser import launch

launch()                       # macOS → macos-native
launch(persona="macos-native")
launch(persona="mac-native")   # same preset
```

Timezone, locale, languages, and WebRTC IP still follow **GeoIP** from the egress IP (default on). Explicit `timezone=` / `locale=` win.

UA is Chrome **151.0.7922.174**.

## No `macos-chrome`

There is no sampled macOS Chrome preset. Do not add one in bindings.

## Remap

`macos-native` (or `mac-native`) on Linux or Windows remaps to that host’s native (`linux-native` / `windows-native`).
