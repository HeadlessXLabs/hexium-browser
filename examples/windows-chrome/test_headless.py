"""Headless windows-chrome persona: Vercel detector, then Infosimples, same tab, record video.

Usage:
    python examples/windows-chrome/test_headless.py
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from headless_oracles import run

if __name__ == "__main__":
    run(recording_name="test_headless_win", persona="windows-chrome")
