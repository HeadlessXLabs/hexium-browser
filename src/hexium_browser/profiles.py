"""Hexium home, named profiles, and launch user-data-dir resolution.

``HEXIUM_HOME`` (default ``~/.hexium``) holds ``config.json`` and ``profiles/``.
Binary cache uses ``HEXIUM_CACHE_DIR`` via ``config.get_cache_dir`` — profiles
never read that env; keep this module free of ``config`` / ``browser`` imports.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

DEFAULT_PROFILE_NAME = "Default"
CONFIG_NAME = "config.json"

_PROFILE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")
_SESSION_PREFIX = "hexium-session-"


def get_hexium_home() -> Path:
    """Return ``HEXIUM_HOME`` or ``~/.hexium``."""
    custom = os.environ.get("HEXIUM_HOME", "").strip()
    if custom:
        return Path(custom).expanduser()
    return Path.home() / ".hexium"


def get_profiles_root() -> Path:
    """Directory for persistent Hexium profiles (never Playwright /tmp tmpfs)."""
    custom = os.environ.get("HEXIUM_PROFILES_DIR", "").strip()
    if custom:
        return Path(custom).expanduser()
    return get_hexium_home() / "profiles"


def get_config_path() -> Path:
    return get_hexium_home() / CONFIG_NAME


def load_config() -> dict:
    path = get_config_path()
    if not path.is_file():
        return {}
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(data: dict) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _validate_profile_name(name: str) -> str:
    if not name or not _PROFILE_NAME_RE.fullmatch(name):
        raise ValueError(
            f"invalid profile name {name!r}: use 1–63 chars, start with a letter "
            "or digit, only letters, digits, '.', '_', '-' (no slashes)."
        )
    return name


def profile_dir(name: str) -> Path:
    return get_profiles_root() / _validate_profile_name(name)


def ensure_profile(name: str) -> Path:
    path = profile_dir(name)
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_profile_names() -> list[str]:
    root = get_profiles_root()
    if not root.is_dir():
        return []
    names: list[str] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith(_SESSION_PREFIX):
            continue
        if _PROFILE_NAME_RE.fullmatch(name):
            names.append(name)
    return sorted(names)


def get_last_profile_name() -> str:
    value = load_config().get("last_profile")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_PROFILE_NAME


def set_last_profile_name(name: str) -> None:
    _validate_profile_name(name)
    data = load_config()
    data["last_profile"] = name
    save_config(data)


def is_forbidden_tmp_path(path: Path) -> bool:
    resolved = path.expanduser().resolve()
    tmp_roots = [Path("/tmp").resolve(), Path("/var/tmp").resolve()]
    tmpdir = os.environ.get("TMPDIR", "").strip()
    if tmpdir:
        tmp_roots.append(Path(tmpdir).expanduser().resolve())
    return any(root == resolved or root in resolved.parents for root in tmp_roots)


def assert_persistent_profile(path: Path) -> Path:
    """Refuse /tmp user-data-dir unless explicitly pinned or allowed."""
    resolved = path.expanduser().resolve()
    if os.environ.get("HEXIUM_ALLOW_TMP_PROFILE", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    tmp_roots = [Path("/tmp").resolve(), Path("/var/tmp").resolve()]
    pinned: list[Path] = []
    for key in ("HEXIUM_HOME", "HEXIUM_PROFILES_DIR", "HEXIUM_USER_DATA_DIR"):
        val = os.environ.get(key, "").strip()
        if val:
            pinned.append(Path(val).expanduser().resolve())

    under_tmp = any(root == resolved or root in resolved.parents for root in tmp_roots)
    allowed_pin = any(pin == resolved or pin in resolved.parents for pin in pinned)
    if under_tmp and not allowed_pin:
        raise RuntimeError(
            f"user_data_dir {resolved} is under /tmp (tmpfs looks like Incognito). "
            "Use ~/.hexium/profiles or set HEXIUM_USER_DATA_DIR to a real disk."
        )
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _new_session_dir() -> Path:
    root = get_profiles_root()
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=_SESSION_PREFIX, dir=str(root)))


def resolve_launch_user_data_dir(
    user_data_dir: str | os.PathLike | None = None,
    *,
    profile: str | None = None,
    ephemeral: bool = False,
) -> Path:
    """Profile dir for ``launch()``. Never Incognito; never reuse ``last_profile`` on bare launch."""
    if user_data_dir is not None:
        return assert_persistent_profile(Path(os.fspath(user_data_dir)))

    pinned = os.environ.get("HEXIUM_USER_DATA_DIR", "").strip()
    if pinned:
        return assert_persistent_profile(Path(pinned))

    if ephemeral:
        return assert_persistent_profile(_new_session_dir())

    if profile is not None:
        path = ensure_profile(profile)
        set_last_profile_name(profile)
        return assert_persistent_profile(path)

    return assert_persistent_profile(_new_session_dir())
