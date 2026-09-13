"""Binary download and cache management for hexium_browser.

Resolution order for ``ensure_binary()``:
1. ``HEXIUM_BINARY_PATH`` env (or alias ``HEXIUM_BINARY``; error if missing)
2. ``$HEXIUM_OUT/hexium-v{VERSION}/chrome`` when the file exists
   (archive artifact: ``$HEXIUM_OUT/hexium-v{VERSION}/Hexium-{VERSION}-{platform}{ext}``)
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
    GITHUB_RELEASES_REPO,
    check_platform_available,
    get_default_hexium_binary_path,
    get_archive_ext,
    get_binary_dir,
    get_binary_path,
    get_cache_dir,
    get_chromium_version,
    get_download_url,
    get_download_urls,
    get_effective_version,
    get_github_download_url,
    get_local_binary_override,
    get_platform_tag,
    hexium_engine_release_tag,
    normalize_requested_version,
    parse_hexium_engine_tag,
)

logger = logging.getLogger("hexium_browser")

DOWNLOAD_TIMEOUT = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=10.0)
DOWNLOAD_ATTEMPTS = 3


def _missing_binary_message() -> str:
    version = get_effective_version()
    return (
        "Hexium browser binary not found.\n\n"
        "Options:\n"
        "  1. Run: hexium-browser fetch\n"
        f"     {get_github_download_url(version)}\n"
        "  2. Set HEXIUM_BINARY_PATH to an unpacked chrome executable\n"
        "  3. Set HEXIUM_OUT if you already have a local engine out dir\n"
    )


def ensure_binary(
    browser_version: str | None = None, *, allow_download: bool = False
) -> str:
    """Ensure the Hexium Chromium binary is available. Returns executable path.

  By default does not download — use ``hexium-browser fetch`` or pass
  ``allow_download=True``. Fetch tries GitHub Releases in CI, otherwise the
  API host then GitHub. Any failed URL (including connection reset) tries the next.
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
    resolved = _download_and_extract(version)
    binary_path = get_binary_path(resolved)

    if not (binary_path.exists() and _is_executable(binary_path)):
        raise RuntimeError(_missing_binary_message())

    return str(binary_path)


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "hexium-browser",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("HEXIUM_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token.strip()}"
    return headers


def fetch_latest_engine_version() -> str | None:
    """Newest GitHub tag ``Hexium-{VERSION}``. Ignores Python ``v0.1.0`` releases."""
    url = f"https://api.github.com/repos/{GITHUB_RELEASES_REPO}/releases?per_page=30"
    try:
        response = httpx.get(url, headers=_github_headers(), timeout=DOWNLOAD_TIMEOUT)
        response.raise_for_status()
        rows = response.json()
    except Exception as exc:
        logger.warning("Could not list GitHub Hexium releases: %s", exc)
        return None
    if not isinstance(rows, list):
        return None
    best: tuple[int, ...] | None = None
    best_version: str | None = None
    for row in rows:
        if not isinstance(row, dict) or row.get("draft") or row.get("prerelease"):
            continue
        version = parse_hexium_engine_tag(str(row.get("tag_name") or ""))
        if not version:
            continue
        try:
            key = tuple(int(part) for part in version.split("."))
        except ValueError:
            continue
        if best is None or key > best:
            best = key
            best_version = version
    return best_version


def _download_and_extract(version: str | None = None) -> str:
    """Try each download URL. Network errors fall through to the next host."""
    pinned = version or get_effective_version()
    candidates: list[str] = [pinned]
    latest = fetch_latest_engine_version()
    if latest and latest not in candidates:
        candidates.append(latest)

    errors: list[str] = []
    for engine_version in candidates:
        urls = get_download_urls(engine_version)
        binary_dir = get_binary_dir(engine_version)
        binary_path = get_binary_path(engine_version)
        binary_dir.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=get_archive_ext(), delete=False) as tmp:
            tmp_path = Path(tmp.name)
        downloaded = False
        try:
            for url in urls:
                if _try_download(url, tmp_path, errors):
                    downloaded = True
                    break
            if not downloaded:
                continue
            _extract_archive(tmp_path, binary_dir, binary_path)
            return engine_version
        except Exception as exc:
            errors.append(f"{engine_version} extract: {exc}")
        finally:
            tmp_path.unlink(missing_ok=True)

    tried = "; ".join(errors) if errors else "no URLs"
    raise RuntimeError(
        f"Could not download Hexium binary (tried {hexium_engine_release_tag(pinned)}"
        f" then latest Hexium-* tag). {tried}\n\n{_missing_binary_message()}"
    )


def _try_download(url: str, dest: Path, errors: list[str]) -> bool:
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            _download_file(url, dest)
            return True
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            logger.warning("Download %s failed HTTP %s", url, status)
            errors.append(f"{url}: HTTP {status}")
            if status in {401, 403, 404, 410}:
                return False
            if attempt < DOWNLOAD_ATTEMPTS:
                time.sleep(attempt)
        except (httpx.HTTPError, OSError) as exc:
            logger.warning(
                "Download %s failed (attempt %s/%s): %s",
                url,
                attempt,
                DOWNLOAD_ATTEMPTS,
                exc,
            )
            errors.append(f"{url}: {exc}")
            if attempt < DOWNLOAD_ATTEMPTS:
                time.sleep(attempt)
    return False


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
            extract_kwargs = {}
            if sys.version_info >= (3, 12):
                extract_kwargs["filter"] = "data"
            tar.extractall(dest_dir, members=safe_members, **extract_kwargs)


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


def _download_meta(version: str | None = None) -> dict:
    v = version or get_effective_version()
    return {
        "download_url": get_download_url(v),
        "github_download_url": get_github_download_url(v),
        "download_urls": get_download_urls(v),
        "engine_tag": hexium_engine_release_tag(v),
    }


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
            **_download_meta(),
            "source": "HEXIUM_BINARY_PATH",
        }

    default_path = Path(get_default_hexium_binary_path())
    if default_path.exists():
        version = get_effective_version()
        return {
            "version": version,
            "platform": get_platform_tag(),
            "binary_path": str(default_path),
            "installed": True,
            "cache_dir": None,
            **_download_meta(version),
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
        **_download_meta(version),
        "source": "cache",
    }


def check_for_update() -> str | None:
    """Return a newer Hexium-* GitHub tag than the pinned engine, if any."""
    current = get_effective_version()
    latest = fetch_latest_engine_version()
    if not latest or latest == current:
        return None
    try:
        cur = tuple(int(p) for p in current.split("."))
        new = tuple(int(p) for p in latest.split("."))
    except ValueError:
        return latest
    return latest if new > cur else None
