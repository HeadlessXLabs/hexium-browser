"""Binary download and cache management for hexium_browser.

Resolution order for ``ensure_binary()``:
1. ``HEXIUM_BINARY_PATH`` env (or alias ``HEXIUM_BINARY``; error if missing)
2. ``$HEXIUM_OUT/hexium-v{VERSION}/chrome`` when the file exists
   (archive artifact: ``$HEXIUM_OUT/hexium-v{VERSION}/hexium-{platform}{ext}``)
3. Cached binary under ``~/.hexium/hexium-v{VERSION}/``
4. Download only when ``allow_download=True`` (``hexium-browser fetch``)
"""

from __future__ import annotations

import hashlib
import logging
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

import httpx

from .config import (
    check_platform_available,
    get_default_hexium_binary_path,
    get_archive_ext,
    get_binary_dir,
    get_binary_path,
    get_cache_dir,
    get_chromium_version,
    get_download_url,
    get_effective_version,
    get_local_binary_override,
    get_platform_tag,
    normalize_requested_version,
)

logger = logging.getLogger("hexium_browser")

DOWNLOAD_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)


def _missing_binary_message() -> str:
    return (
        "Hexium browser binary not found.\n\n"
        "Options:\n"
        f"  1. Build the engine and set HEXIUM_BINARY_PATH\n"
        f"  2. Use the default out path if built: {get_default_hexium_binary_path()}\n"
        "     Archive: $HEXIUM_OUT/hexium-v{VERSION}/hexium-{platform}{ext}\n"
        f"  3. Run: hexium-browser fetch  (when headlessx.dev tarballs are available)\n"
    )


def ensure_binary(
    browser_version: str | None = None, *, allow_download: bool = False
) -> str:
    """Ensure the Hexium Chromium binary is available. Returns executable path.

  By default does not download — use ``hexium-browser fetch`` or pass
  ``allow_download=True`` once headlessx.dev tarballs exist.
    """
    override = get_local_binary_override()
    if override:
        path = Path(override)
        if not path.exists():
            raise FileNotFoundError(
                f"HEXIUM_BINARY_PATH set to '{override}' but file does not exist"
            )
        logger.info("Using HEXIUM_BINARY_PATH: %s", override)
        return str(path)

    default_path = Path(get_default_hexium_binary_path())
    if default_path.exists() and _is_executable(default_path):
        logger.info("Using default local Hexium binary: %s", default_path)
        return str(default_path)

    requested_version = normalize_requested_version(browser_version)
    version = requested_version or get_effective_version()
    binary_path = get_binary_path(version)

    if binary_path.exists() and _is_executable(binary_path):
        logger.debug("Binary found in cache: %s (version %s)", binary_path, version)
        return str(binary_path)

    if not allow_download:
        raise FileNotFoundError(_missing_binary_message())

    check_platform_available()

    logger.info(
        "Hexium %s not found. Downloading for %s...",
        version,
        get_platform_tag(),
    )
    _download_and_extract(version)

    if not (binary_path.exists() and _is_executable(binary_path)):
        raise RuntimeError(_missing_binary_message())

    return str(binary_path)


def _download_and_extract(version: str | None = None) -> None:
    """Download from headlessx.dev and extract into the cache directory."""
    url = get_download_url(version)
    binary_dir = get_binary_dir(version)
    binary_path = get_binary_path(version)
    binary_dir.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=get_archive_ext(), delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        _download_file(url, tmp_path)
        # TODO: verify checksum/signature from the same HEXIUM_DOWNLOAD_URL tree.
        _extract_archive(tmp_path, binary_dir, binary_path)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise RuntimeError(
                f"Download failed (404): {url}\n\n{_missing_binary_message()}"
            ) from exc
        raise RuntimeError(f"Download failed: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(
            f"Could not download Hexium binary from {url}\n\n{_missing_binary_message()}"
        ) from exc
    finally:
        tmp_path.unlink(missing_ok=True)


def _download_file(url: str, dest: Path) -> None:
    logger.info("Downloading from %s", url)
    with httpx.stream(
        "GET", url, follow_redirects=True, timeout=DOWNLOAD_TIMEOUT
    ) as response:
        response.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)
    logger.info("Download complete: %d MB", dest.stat().st_size // (1024 * 1024))


def _extract_archive(
    archive_path: Path, dest_dir: Path, binary_path: Path | None = None
) -> None:
    logger.info("Extracting to %s", dest_dir)
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    if str(archive_path).endswith(".zip"):
        _extract_zip(archive_path, dest_dir)
    else:
        _extract_tar(archive_path, dest_dir)

    _flatten_single_subdir(dest_dir)
    bp = binary_path or get_binary_path()
    if bp.exists():
        _make_executable(bp)
    if platform.system() == "Darwin":
        _remove_quarantine(dest_dir)
    if bp.exists():
        logger.info("Binary ready: %s", bp)


def _extract_tar(archive_path: Path, dest_dir: Path) -> None:
    with tarfile.open(archive_path, "r:gz") as tar:
        safe_members = []
        for member in tar.getmembers():
            if member.issym() or member.islnk():
                link_target = member.linkname
                if os.path.isabs(link_target) or ".." in link_target.split("/"):
                    continue
            else:
                member_path = (dest_dir / member.name).resolve()
                if not str(member_path).startswith(str(dest_dir.resolve())):
                    raise RuntimeError(f"Archive contains path traversal: {member.name}")
            safe_members.append(member)
        tar.extractall(dest_dir, members=safe_members)


def _extract_zip(archive_path: Path, dest_dir: Path) -> None:
    import zipfile

    with zipfile.ZipFile(archive_path, "r") as zf:
        for info in zf.infolist():
            member_path = (dest_dir / info.filename).resolve()
            if not str(member_path).startswith(str(dest_dir.resolve())):
                raise RuntimeError(f"Archive contains path traversal: {info.filename}")
        zf.extractall(dest_dir)


def _flatten_single_subdir(dest_dir: Path) -> None:
    entries = list(dest_dir.iterdir())
    if len(entries) == 1 and entries[0].is_dir():
        subdir = entries[0]
        if subdir.name.endswith(".app"):
            return
        for item in subdir.iterdir():
            shutil.move(str(item), str(dest_dir / item.name))
        subdir.rmdir()


def _is_executable(path: Path) -> bool:
    try:
        return os.access(path, os.X_OK)
    except OSError:
        return False


def _make_executable(path: Path) -> None:
    if platform.system() == "Windows":
        return
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _remove_quarantine(path: Path) -> None:
    try:
        subprocess.run(["xattr", "-cr", str(path)], capture_output=True, timeout=30)
    except Exception:
        pass


def clear_cache() -> None:
    cache_dir = get_cache_dir()
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        logger.info("Cache cleared: %s", cache_dir)


def binary_info(browser_version: str | None = None) -> dict:
    """Return info about the current binary installation."""
    requested = normalize_requested_version(browser_version)
    override = get_local_binary_override()
    if override:
        return {
            "version": None,
            "platform": get_platform_tag(),
            "binary_path": override,
            "installed": os.path.isfile(override),
            "cache_dir": None,
            "download_url": get_download_url(),
            "source": "HEXIUM_BINARY_PATH",
        }

    default_path = Path(get_default_hexium_binary_path())
    if default_path.exists():
        return {
            "version": get_effective_version(),
            "platform": get_platform_tag(),
            "binary_path": str(default_path),
            "installed": True,
            "cache_dir": None,
            "download_url": get_download_url(),
            "source": "HEXIUM_OUT",
        }

    version = requested or get_effective_version()
    binary_path = get_binary_path(version)
    return {
        "version": version,
        "platform": get_platform_tag(),
        "binary_path": str(binary_path),
        "installed": binary_path.exists(),
        "cache_dir": str(get_binary_dir(version)),
        "download_url": get_download_url(version),
        "source": "cache",
    }


def check_for_update() -> str | None:
    """Placeholder for future auto-update from headlessx.dev."""
    # TODO: query headlessx.dev for newer engine versions.
    return None
