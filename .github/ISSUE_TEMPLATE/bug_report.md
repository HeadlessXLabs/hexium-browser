---
name: Bug report
about: Wrapper, launch, persona, or detection issue
labels: bug
---

**hexium-browser version:** <!-- pip show hexium-browser -->

**Engine:** <!-- hexium-browser info --quick -->

**OS / arch:**

**Persona:** <!-- linux-native (default on Linux), windows-native, macos-native, linux-chrome, windows-chrome -->

**Headless?** <!-- yes / no (headed) -->

**Proxy?** <!-- no / http / socks5 (no credentials) -->

**What happened:**


**What you expected:**


**Minimal repro:**

```python
from hexium_browser import launch

browser = launch(headless=True)
page = browser.new_page()
# ...
browser.close()
```

**Logs / screenshots:**

Do not paste secrets, cookies, or internal build paths.
