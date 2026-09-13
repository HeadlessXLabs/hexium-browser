# Personas

`launch(persona=…)` or `HEXIUM_PERSONA`. Defaults follow the **host OS**. Opt-in `*-chrome` presets are never remapped. There is no `macos-chrome`.

| Preset | Default on | Notes |
| --- | --- | --- |
| [linux-native](linux-native.md) | Linux | This machine |
| [windows-native](windows-native.md) | Windows | This machine |
| [macos-native](macos-native.md) | macOS | This machine. Alias `mac-native`. |
| [linux-chrome](linux-chrome.md) | — | Opt-in Linux sampled screen/CPU; host GPU/fonts |
| [windows-chrome](windows-chrome.md) | — | Opt-in Win32 + D3D + Segoe. Alias `windows-1080p`. |

Wrong-OS `*-native` remaps to the host native (example: `windows-native` on Linux → `linux-native`). UA is Chrome **151.0.7922.174**. GeoIP still fills timezone/locale from the egress IP.

On Linux, `windows-chrome` has a known WebGL **pixel-vs-name** tell (about −5%). It is not claimed fixed. Full launch contract: [USAGE.md](../USAGE.md).

## Headless captures

13 Sep 2026. Same walks as the [README test results](../../README.md#test-results).

| [`linux-native`](linux-native.md) | [`windows-chrome`](windows-chrome.md) |
| --- | --- |
| ![Linux Vercel](../../assets/screenshots/test_headless_linux_vercel.png) | ![Win32 Vercel](../../assets/screenshots/test_headless_win_vercel.png) |
| Detector **0.10**, Normal Browser | Detector **0.00**, Normal Browser |
