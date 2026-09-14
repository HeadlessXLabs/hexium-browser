"""Headed whoer.net — linux-native, rotating HTTP proxy, ephemeral random profile.

Usage:
    export DISPLAY=:0
    export HEXIUM_BINARY_PATH="${HEXIUM_OUT}/chrome"
    export HEXIUM_PROXY='http://USER:PASS@host:port'   # rotating pool, no session pin
    python examples/linux-native/whoer_headed_http_proxy_ephemeral_random_profile.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from whoer_common import run_whoer


def main() -> None:
    run_whoer(
        persona="linux-native",
        screenshot_name="whoer_headed_linux_native.png",
    )


if __name__ == "__main__":
    main()
