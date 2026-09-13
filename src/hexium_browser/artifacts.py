"""Where example/oracle artifacts land (screenshots + Playwright video)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

# Repo checkout: <repo>/src/hexium_browser/artifacts.py → <repo>/assets/
_REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_ROOT = Path(os.environ["HEXIUM_ARTIFACTS_DIR"]) if os.environ.get("HEXIUM_ARTIFACTS_DIR") else _REPO_ROOT / "assets"
SCREENSHOTS_DIR = ARTIFACTS_ROOT / "screenshots"
RECORDINGS_DIR = ARTIFACTS_ROOT / "recordings"

_FALLBACK_VIDEO_SIZE = {"width": 1920, "height": 1080}


def ensure_artifact_dirs() -> tuple[Path, Path]:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    return SCREENSHOTS_DIR, RECORDINGS_DIR


def detect_screen_size() -> dict[str, int]:
    """Physical display size so Playwright video matches the window.

    Headed Hexium uses ``no_viewport``. Playwright then records 800x800 unless
    ``record_video_size`` (and a matching ``viewport``) are set explicitly.
    """
    env_w = os.environ.get("HEXIUM_VIDEO_WIDTH")
    env_h = os.environ.get("HEXIUM_VIDEO_HEIGHT")
    if env_w and env_h:
        return {"width": int(env_w), "height": int(env_h)}
    try:
        out = subprocess.check_output(
            ["xrandr", "--current"], text=True, timeout=2, stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            if "*" not in line:
                continue
            match = re.search(r"(\d{3,5})x(\d{3,5})", line)
            if match:
                return {"width": int(match.group(1)), "height": int(match.group(2))}
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return dict(_FALLBACK_VIDEO_SIZE)


def _scratch_dir(name: str) -> Path:
    _, recs = ensure_artifact_dirs()
    scratch = recs / f".tmp-{name}"
    if scratch.exists():
        shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir(parents=True, exist_ok=True)
    return scratch


def recording_kwargs(name: str) -> dict[str, Any]:
    """``launch()`` kwargs so recorded video is 1:1 with the page.

    Playwright writes ``page@<hash>.webm`` into a scratch folder. Call
    :func:`finalize_recording` after ``browser.close()`` to save a stable name
    that overwrites on the next run.
    """
    size = detect_screen_size()
    return {
        "record_video_dir": str(_scratch_dir(name)),
        "record_video_size": size,
        "viewport": size,
    }


def finalize_recording(video: Any, name: str) -> Path | None:
    """Copy the Playwright video to ``assets/recordings/<name>.webm`` and drop leftovers."""
    ensure_artifact_dirs()
    dest = RECORDINGS_DIR / f"{name}.webm"
    scratch = RECORDINGS_DIR / f".tmp-{name}"
    if dest.exists():
        dest.unlink()
    saved = False
    if video is not None:
        try:
            video.save_as(str(dest))
            saved = dest.is_file() and dest.stat().st_size > 0
        except Exception:
            saved = False
    if not saved and scratch.is_dir():
        webms = sorted(scratch.glob("*.webm"), key=lambda p: p.stat().st_mtime)
        if webms:
            shutil.move(str(webms[-1]), str(dest))
            saved = dest.is_file()
    if scratch.exists():
        shutil.rmtree(scratch, ignore_errors=True)
    for leftover in RECORDINGS_DIR.glob("page@*.webm"):
        leftover.unlink(missing_ok=True)
    return dest if saved else None
