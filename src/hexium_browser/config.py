"""Stealth configuration and platform detection for hexium_browser."""

from __future__ import annotations

import json
import logging
import os
import platform
import random
import re
from pathlib import Path

from .profiles import get_profiles_root, resolve_launch_user_data_dir

logger = logging.getLogger("hexium_browser")


# ---------------------------------------------------------------------------
# Engine version shipped with this release.
# ---------------------------------------------------------------------------
CHROMIUM_VERSION = "151.0.7922.174.1"

PLATFORM_CHROMIUM_VERSIONS: dict[str, str] = {
    "linux-x64": "151.0.7922.174.1",
    "linux-arm64": "151.0.7922.174.1",
    "darwin-arm64": "151.0.7922.174.1",
    "darwin-x64": "151.0.7922.174.1",
    "windows-x64": "151.0.7922.174.1",
}

# Optional local out root. Only used when HEXIUM_OUT is set.

# ---------------------------------------------------------------------------
# Playwright default args to suppress — these leak automation signals.
# ---------------------------------------------------------------------------
IGNORE_DEFAULT_ARGS = [
    "--enable-automation",
    "--enable-unsafe-swiftshader",
    "--disable-extensions",
]


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def allow_3p_cookies_enabled(explicit: bool | None = None) -> bool:
    """HX-P4-04: optional ``--hexium-allow-3p-cookies``. Default off.

    Launch ``allow_3p_cookies=True``/``False`` wins when set. Otherwise
    ``HEXIUM_ALLOW_3P_COOKIES=1`` (or true/yes/on) enables the flag.
    """
    if explicit is not None:
        return bool(explicit)
    return _env_truthy("HEXIUM_ALLOW_3P_COOKIES")


def linux_headed_gui_args() -> list[str]:
    """GTK4 + X11 so headed Chrome does not SIGSEGV on Lingmo GTK3.

    System Chromium on this host gets ``--gtk-version=4`` from
    ``/etc/chromium.d/gtk4-fix``. A self-built Hexium ``chrome`` does not
    read that file. Headless does not need these flags. Override with extra
    launch args or ``HEXIUM_NO_GTK4=1``.
    """
    if platform.system() != "Linux" or _env_truthy("HEXIUM_NO_GTK4"):
        return []
    args = ["--gtk-version=4"]
    if os.environ.get("DISPLAY"):
        args.append("--ozone-platform=x11")
    return args


def linux_headless_gl_args() -> list[str]:
    """Headless Linux: do not force software GL (SwiftShader / llvmpipe).

    Playwright's ``--enable-unsafe-swiftshader`` is dropped via
    ``IGNORE_DEFAULT_ARGS``. Software UNMASKED_RENDERER strings are masked
    in the engine overlay; the wrapper does not pass ``--disable-gpu`` or
    ``--use-gl=swiftshader``.
    """
    if platform.system() != "Linux":
        return []
    return []


def apply_linux_headed_gui_env(env: dict[str, str] | None = None) -> dict[str, str] | None:
    """GTK_CSD=0 only. Do not set GTK_THEME — Appearance must stay Classic.

    ``--gtk-version=4`` is a library version (Lingmo SIGSEGV). It is not the
    Settings → Appearance → Theme dropdown. That dropdown is Classic
    (HX-P3-06 in the engine; ``seed_classic_theme_prefs`` for profiles).
    """
    if platform.system() != "Linux" or _env_truthy("HEXIUM_NO_GTK4"):
        return env
    out = dict(env) if env is not None else dict(os.environ)
    out.setdefault("GTK_CSD", "0")
    return out


# ui::SystemTheme::kDefault — Settings → Appearance → Theme → Classic on Linux.
_CLASSIC_SYSTEM_THEME = 0


def seed_classic_theme_prefs(user_data_dir: str | os.PathLike) -> None:
    """Force Classic theme in a persistent profile before Chrome starts.

    Writes ``extensions.theme.system_theme=0`` and clears ``extensions.theme.id``.
    Engine HX-P3-06 also locks this; the pref covers profiles that Chrome
    would otherwise initialize as GTK. No-op on non-Linux or empty path.
    Never raises.
    """
    if platform.system() != "Linux" or not user_data_dir:
        return
    try:
        prefs_path = Path(os.fspath(user_data_dir)) / "Default" / "Preferences"
        prefs_path.parent.mkdir(parents=True, exist_ok=True)
        data: dict = {}
        if prefs_path.is_file():
            raw = prefs_path.read_text(encoding="utf-8").strip()
            if raw:
                loaded = json.loads(raw)
                if isinstance(loaded, dict):
                    data = loaded
        theme = data.setdefault("extensions", {}).setdefault("theme", {})
        if not isinstance(theme, dict):
            theme = {}
            data.setdefault("extensions", {})["theme"] = theme
        theme["system_theme"] = _CLASSIC_SYSTEM_THEME
        theme["id"] = ""
        prefs_path.write_text(json.dumps(data), encoding="utf-8")
    except (OSError, TypeError, ValueError):
        return


_NATIVE_PRESET_HOST = {
    "linux-native": "Linux",
    "windows-native": "Windows",
    "macos-native": "Darwin",
}


def _host_native_persona() -> str:
    """Host default native preset. Does not read ``HEXIUM_PERSONA``."""
    system = platform.system()
    if system == "Darwin":
        return "macos-native"
    if system == "Linux":
        return "linux-native"
    return "windows-native"


def _default_persona() -> str:
    """Return the default ``--hexium-persona`` value.

    ``HEXIUM_PERSONA`` overrides (then aliases + wrong-OS native remap).
    Linux default is ``linux-native``; Windows ``windows-native``; macOS
    ``macos-native``. Pass ``windows-chrome`` or ``linux-chrome`` to sample.
    """
    override = os.environ.get("HEXIUM_PERSONA", "").strip()
    if override:
        return normalize_persona_preset(override)
    return _host_native_persona()


def normalize_persona_preset(name: str) -> str:
    """Map aliases onto canonical names and coerce wrong-OS natives.

    ``windows-1080p`` aliases ``windows-chrome``. ``mac-native`` aliases
    ``macos-native``. A ``*-native`` name that does not match this OS is
    remapped to the host native. ``windows-chrome`` and ``linux-chrome``
    are never remapped.
    """
    if name == "windows-1080p":
        name = "windows-chrome"
    elif name == "mac-native":
        name = "macos-native"

    expected_host = _NATIVE_PRESET_HOST.get(name)
    if expected_host is not None and platform.system() != expected_host:
        host = _host_native_persona()
        logger.warning(
            "persona %s does not match this OS; remapping to %s",
            name,
            host,
        )
        return host
    return name


def get_default_stealth_args(fingerprint: str | None = None) -> list[str]:
    """Build stealth args with a Hexium seed (auto-generated when omitted).

    ``fingerprint="off"`` disables engine fingerprint patches (A/B vs stock Chrome).
    Linux default is ``linux-native``; Windows ``windows-native``; macOS
    ``macos-native``.
    """
    if fingerprint == "off":
        return ["--no-sandbox", "--hexium-fingerprint=off"]

    seed = fingerprint if fingerprint else str(random.randint(10000, 99999))
    return [
        "--no-sandbox",
        f"--hexium-seed={seed}",
        f"--hexium-persona={_default_persona()}",
    ]


DEFAULT_VIEWPORT = {"width": 1920, "height": 947}

SUPPORTED_PLATFORMS: dict[tuple[str, str], str] = {
    ("Linux", "x86_64"): "linux-x64",
    ("Linux", "aarch64"): "linux-arm64",
    ("Darwin", "arm64"): "darwin-arm64",
    ("Darwin", "x86_64"): "darwin-x64",
    ("Windows", "AMD64"): "windows-x64",
    ("Windows", "x86_64"): "windows-x64",
}

# v0.1 first ship: linux-x64 only; other platforms error until tarball exists.
AVAILABLE_PLATFORMS: set[str] = {"linux-x64"}

_VERSION_PIN_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){3,4}$")


def normalize_requested_version(version: str | None = None) -> str | None:
    """Return an explicit engine version pin from arg/env, or None."""
    raw = version if version is not None else os.environ.get("HEXIUM_VERSION")
    if raw is None:
        return None
    normalized = raw.strip()
    if not normalized:
        return None
    if not _VERSION_PIN_RE.fullmatch(normalized):
        raise ValueError(
            "Invalid browser version pin. Use a full numeric engine version, "
            "e.g. '151.0.7922.174.1'."
        )
    return normalized


def get_chromium_version() -> str:
    """Return the engine version for the current platform."""
    tag = get_platform_tag()
    return PLATFORM_CHROMIUM_VERSIONS.get(tag, CHROMIUM_VERSION)


def get_platform_tag() -> str:
    """Return the platform tag for binary download (e.g. 'linux-x64')."""
    system = platform.system()
    machine = platform.machine()
    tag = SUPPORTED_PLATFORMS.get((system, machine))
    if tag is None:
        raise RuntimeError(
            f"Unsupported platform: {system} {machine}. "
            f"Supported: {', '.join(f'{s}-{m}' for (s, m) in SUPPORTED_PLATFORMS)}"
        )
    return tag


def get_cache_dir() -> Path:
    """Return the cache directory for downloaded binaries (~/.hexium by default)."""
    custom = os.environ.get("HEXIUM_CACHE_DIR")
    if custom:
        return Path(custom)
    return Path.home() / ".hexium"


def get_hexium_out_root() -> Path:
    """Local engine out dir when ``HEXIUM_OUT`` is set; otherwise unused."""
    custom = os.environ.get("HEXIUM_OUT")
    if custom and custom.strip():
        return Path(custom.strip())
    return Path.home() / ".hexium" / "local-out"


def hexium_out_dir_name(version: str | None = None, tag: str | None = None) -> str:
    """Return ``hexium-v{VERSION}`` (e.g. ``hexium-v151.0.7922.174.1``).

    Same folder name as download URLs and ``~/.hexium``. ``tag`` is unused;
    kept so callers that previously passed a platform tag still work.
    """
    _ = tag  # naming is version-only; platform is in the archive filename
    v = version or get_effective_version()
    return f"hexium-v{v}"


def _gn_chrome_name() -> str:
    if platform.system() == "Windows":
        return "chrome.exe"
    return "chrome"


def _cached_binary_relative() -> Path:
    """Relative executable path inside ``hexium-v{VERSION}/`` (out or cache)."""
    if platform.system() == "Darwin":
        return Path("Hexium.app") / "Contents" / "MacOS" / "Hexium"
    if platform.system() == "Windows":
        return Path("chrome.exe")
    return Path("chrome")


def get_default_hexium_binary_path(version: str | None = None) -> str:
    """Local engine out: ``$HEXIUM_OUT/hexium-v{VERSION}/chrome``.

    After extract: ``chrome`` (Linux), ``chrome.exe`` (Windows), ``Hexium.app``
    (Darwin) — same layout as ``~/.hexium/hexium-v{VERSION}/``. If that file
    is missing, fall back to legacy ``Hexium/chrome`` or ``$HEXIUM_OUT/chrome``.
    """
    for path in default_hexium_binary_candidates(version):
        if path.is_file():
            return str(path)
    return str(default_hexium_binary_candidates(version)[0])


def default_hexium_binary_candidates(version: str | None = None) -> list[Path]:
    """Preferred then legacy local-out locations for ``chrome``."""
    name = _gn_chrome_name()
    root = get_hexium_out_root()
    tagged_dir = root / hexium_out_dir_name(version)
    tagged = tagged_dir / _cached_binary_relative()
    seen: set[str] = set()
    out: list[Path] = []
    for path in (tagged, tagged_dir / name, root / "Hexium" / name, root / name):
        key = str(path)
        if key not in seen:
            seen.add(key)
            out.append(path)
    return out


def get_binary_dir(version: str | None = None) -> Path:
    """Return the directory for a Hexium engine version binary."""
    v = version or get_chromium_version()
    return get_cache_dir() / f"hexium-v{v}"


def get_binary_path(version: str | None = None) -> Path:
    """Return the expected path to the chrome executable."""
    return get_binary_dir(version) / _cached_binary_relative()


def check_platform_available() -> None:
    """Raise a clear error if no pre-built binary exists for this platform."""
    if get_local_binary_override():
        return
    for path in default_hexium_binary_candidates():
        if path.is_file():
            return

    tag = get_platform_tag()
    if tag not in AVAILABLE_PLATFORMS:
        available = ", ".join(sorted(AVAILABLE_PLATFORMS))
        raise RuntimeError(
            f"No pre-built Hexium binary for {tag}. "
            f"Currently available: {available}. "
            f"Build the engine and set HEXIUM_BINARY_PATH, or use the default "
            f"dev path if present: {get_default_hexium_binary_path()}"
        )


def get_effective_version() -> str:
    """Return the pinned or platform default engine version."""
    try:
        requested = normalize_requested_version()
    except ValueError:
        requested = None
    if requested:
        return requested
    return get_chromium_version()


def _version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def _version_newer(a: str, b: str) -> bool:
    return _version_tuple(a) > _version_tuple(b)


DOWNLOAD_BASE_URL = os.environ.get(
    "HEXIUM_DOWNLOAD_URL",
    "https://headlessx.dev/api/download",
)

GITHUB_RELEASES_REPO = os.environ.get(
    "HEXIUM_GITHUB_REPO",
    "HeadlessXLabs/hexium-browser",
)
_ENGINE_TAG_RE = re.compile(r"^Hexium-(\d+(?:\.\d+)+)$")


def get_archive_ext() -> str:
    return ".zip" if platform.system() == "Windows" else ".tar.gz"


def get_archive_name(tag: str | None = None, version: str | None = None) -> str:
    """``Hexium-{VERSION}-{platform}.tar.gz`` (Windows: ``.zip``)."""
    t = tag or get_platform_tag()
    v = version or get_chromium_version()
    return f"Hexium-{v}-{t}{get_archive_ext()}"


def get_hexium_out_archive_path(version: str | None = None, tag: str | None = None) -> Path:
    """Local fetch artifact: ``$HEXIUM_OUT/hexium-v{VERSION}/Hexium-{VERSION}-{platform}{ext}``."""
    return get_hexium_out_root() / hexium_out_dir_name(version) / get_archive_name(tag, version)


def hexium_engine_release_tag(version: str | None = None) -> str:
    """GitHub tag that owns the tarball: ``Hexium-{VERSION}``."""
    return f"Hexium-{version or get_chromium_version()}"


def get_download_url(version: str | None = None) -> str:
    """Primary CDN URL (``HEXIUM_DOWNLOAD_URL`` / headlessx.dev)."""
    v = version or get_chromium_version()
    return f"{DOWNLOAD_BASE_URL.rstrip('/')}/hexium-v{v}/{get_archive_name(version=v)}"


def get_github_download_url(version: str | None = None, tag: str | None = None) -> str:
    """GitHub Release asset for this engine version (not the Python ``vX.Y.Z`` tag)."""
    v = version or get_chromium_version()
    archive = get_archive_name(tag, v)
    return (
        f"https://github.com/{GITHUB_RELEASES_REPO}/releases/download/"
        f"{hexium_engine_release_tag(v)}/{archive}"
    )


def prefer_github_download() -> bool:
    """GitHub Actions and ``HEXIUM_FETCH_GITHUB_FIRST`` try Releases before the API host."""
    if _env_truthy("HEXIUM_FETCH_GITHUB_FIRST"):
        return True
    return _env_truthy("GITHUB_ACTIONS")


def get_download_urls(version: str | None = None) -> list[str]:
    """API then GitHub Releases. GitHub first on Actions. Never duplicate URLs."""
    v = version or get_chromium_version()
    api = get_download_url(v)
    github = get_github_download_url(v)
    ordered = (github, api) if prefer_github_download() else (api, github)
    urls: list[str] = []
    for url in ordered:
        if url not in urls:
            urls.append(url)
    return urls


def parse_hexium_engine_tag(tag_name: str) -> str | None:
    """Return the engine version from a ``Hexium-151.0.7922.174.1`` tag, else None."""
    match = _ENGINE_TAG_RE.match((tag_name or "").strip())
    return match.group(1) if match else None


def get_local_binary_override() -> str | None:
    """Local chrome. ``HEXIUM_BINARY_PATH`` wins; ``HEXIUM_BINARY`` is an alias."""
    for key in ("HEXIUM_BINARY_PATH", "HEXIUM_BINARY"):
        raw = os.environ.get(key)
        if raw and raw.strip():
            return raw.strip()
    return None


# Headless no_viewport shim — enable when the engine reports coherent dimensions.
HEADLESS_NO_VIEWPORT_MIN_VERSION: str | None = "151.0.7922.174.1"


def binary_supports_headless_no_viewport(
    browser_version: str | None = None,
) -> bool:
    if HEADLESS_NO_VIEWPORT_MIN_VERSION is None:
        return False
    try:
        declared = normalize_requested_version(browser_version)
    except ValueError:
        declared = None
    if declared:
        version = declared
    elif get_local_binary_override() or Path(get_default_hexium_binary_path()).exists():
        return True
    else:
        version = get_effective_version()
    try:
        return not _version_newer(HEADLESS_NO_VIEWPORT_MIN_VERSION, version)
    except (ValueError, AttributeError):
        return False


# Inline HTTP proxy auth in --proxy-server=user:pass@host is a Cloak-style
# network patch (HX-P2 gap — not in overlay yet). Until it ships, credentialed
# HTTP proxies use Playwright's proxy dict. Opt in after rebuild:
# HEXIUM_HTTP_PROXY_INLINE_AUTH=1
HTTP_PROXY_INLINE_AUTH_FLOOR: dict[str, str] = {
    "linux-x64": "151.0.7922.174.1",
    "windows-x64": "151.0.7922.174.1",
    "linux-arm64": "151.0.7922.174.1",
    "darwin-arm64": "151.0.7922.174.1",
    "darwin-x64": "151.0.7922.174.1",
}


def _http_proxy_inline_auth_enabled() -> bool:
    raw = os.environ.get("HEXIUM_HTTP_PROXY_INLINE_AUTH", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def binary_supports_http_proxy_inline_auth(
    browser_version: str | None = None,
) -> bool:
    if not _http_proxy_inline_auth_enabled():
        return False
    floor = HTTP_PROXY_INLINE_AUTH_FLOOR.get(get_platform_tag())
    if floor is None:
        return False
    try:
        declared = normalize_requested_version(browser_version)
    except ValueError:
        declared = None
    if declared:
        version = declared
    else:
        version = get_effective_version()
    try:
        return not _version_newer(floor, version)
    except (ValueError, AttributeError):
        return False


# Inline SOCKS5 proxy auth in --proxy-server=user:pass@host is a Cloak-style
# network patch (HX-P2-11 gap — not in overlay yet). Until it ships, credentialed
# SOCKS5 proxies use Playwright's proxy dict. Opt in after rebuild:
# HEXIUM_SOCKS_PROXY_INLINE_AUTH=1
SOCKS_PROXY_INLINE_AUTH_FLOOR: dict[str, str] = {
    "linux-x64": "151.0.7922.174.1",
    "windows-x64": "151.0.7922.174.1",
    "linux-arm64": "151.0.7922.174.1",
    "darwin-arm64": "151.0.7922.174.1",
    "darwin-x64": "151.0.7922.174.1",
}


def _socks_proxy_inline_auth_enabled() -> bool:
    raw = os.environ.get("HEXIUM_SOCKS_PROXY_INLINE_AUTH", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def binary_supports_socks_proxy_inline_auth(
    browser_version: str | None = None,
) -> bool:
    if not _socks_proxy_inline_auth_enabled():
        return False
    floor = SOCKS_PROXY_INLINE_AUTH_FLOOR.get(get_platform_tag())
    if floor is None:
        return False
    try:
        declared = normalize_requested_version(browser_version)
    except ValueError:
        declared = None
    if declared:
        version = declared
    else:
        version = get_effective_version()
    try:
        return not _version_newer(floor, version)
    except (ValueError, AttributeError):
        return False


def binary_supports_maximized_window(browser_version: str | None = None) -> bool:
    return binary_supports_headless_no_viewport(browser_version)


def __getattr__(name: str) -> str:
    if name == "DEFAULT_HEXIUM_BINARY_PATH":
        return get_default_hexium_binary_path()
    raise AttributeError(f"module {__name__!r} has no attribute {name}")
