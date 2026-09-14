"""Headed whoer.net — windows-chrome, rotating HTTP proxy, ephemeral random profile.

Usage:
    export DISPLAY=:0
    export HEXIUM_BINARY_PATH="${HEXIUM_OUT}/chrome"
    export HEXIUM_PROXY='http://USER:PASS@host:port'   # rotating pool, no session pin
    python examples/windows-chrome/whoer_headed_http_proxy_ephemeral_random_profile.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from whoer_common import run_whoer


def main() -> None:
    run_whoer(
        persona="windows-chrome",
        screenshot_name="whoer_headed_windows_chrome.png",
    )


if __name__ == "__main__":
    main()
