"""Upgrade Hexium persona zips in-place.

Usage:
    python scripts/upgrade_persona_datapack.py
"""

from __future__ import annotations

from pathlib import Path

from hexium_browser.persona.datapack import upgrade_datapack_dir


def main() -> None:
    data = Path(__file__).resolve().parents[1] / "src" / "hexium_browser" / "persona" / "data"
    upgrade_datapack_dir(data)
    print(f"Upgraded persona datapack in {data}")


if __name__ == "__main__":
    main()
