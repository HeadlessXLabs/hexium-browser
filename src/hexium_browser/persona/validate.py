"""Reject incoherent rows for linux-chrome and windows-chrome personas."""

from __future__ import annotations

import re

from .schema import CHROME_UA_VERSION, MAX_HARDWARE_CONCURRENCY, PersonaDict

_WINDOWS_PLATFORMS = {"Win32", "Win64"}
_RENDERER_WINDOWS_RE = re.compile(r"Direct3D|D3D11|Segoe UI", re.IGNORECASE)
_RENDERER_D3D_RE = re.compile(r"Direct3D|D3D11", re.IGNORECASE)
_RENDERER_MESA_RE = re.compile(r"Mesa|\bOpenGL\b", re.IGNORECASE)
_RENDERER_SOFTWARE_RE = re.compile(
    r"SwiftShader|llvmpipe|Microsoft Basic Render", re.IGNORECASE
)
_MOBILE_UA_RE = re.compile(r"Mobile|Android|iPhone|iPad", re.IGNORECASE)
_WINDOWS_MARKER_FONTS = ("segoe ui", "calibri")
_MIN_DESKTOP_WIDTH = 1024
_MIN_DESKTOP_HEIGHT = 600


class PersonaCoherenceError(ValueError):
    """Sampled persona is internally inconsistent for the requested OS persona."""


def _renderer_blob(persona: PersonaDict) -> str:
    return " ".join(
        str(persona.get(key) or "")
        for key in ("recorded_webgl_renderer", "webgl_renderer")
    )


def _require_chrome_151_desktop(persona: PersonaDict, label: str) -> None:
    product = persona.get("user_agent_product")
    if product != "Chrome":
        raise PersonaCoherenceError(
            f"user_agent_product must be Chrome, got {product!r}"
        )

    ua = str(persona.get("user_agent") or "")
    if CHROME_UA_VERSION not in ua:
        raise PersonaCoherenceError(
            f"UA must be rewritten to {CHROME_UA_VERSION}"
        )
    if _MOBILE_UA_RE.search(ua):
        raise PersonaCoherenceError(f"mobile UA is not valid for {label} desktop")

    width = int(persona.get("screen_width") or 0)
    height = int(persona.get("screen_height") or 0)
    if width < _MIN_DESKTOP_WIDTH or height < _MIN_DESKTOP_HEIGHT:
        raise PersonaCoherenceError(
            f"mobile screen {width}x{height} is not valid for {label} desktop"
        )

    cores = int(persona.get("hardware_concurrency") or 0)
    if cores < 1 or cores > MAX_HARDWARE_CONCURRENCY:
        raise PersonaCoherenceError(
            f"hardware_concurrency {cores} is not valid for {label} desktop"
        )


def validate_linux_chrome(persona: PersonaDict) -> None:
    """Raise ``PersonaCoherenceError`` if *persona* is not a Linux Chrome 151 desktop."""
    platform = str(persona.get("platform") or "")
    if platform in _WINDOWS_PLATFORMS:
        raise PersonaCoherenceError(f"Windows platform is not valid for linux-chrome: {platform}")

    ua_ch_platform = str(persona.get("ua_ch_platform") or "")
    if ua_ch_platform.lower() == "windows":
        raise PersonaCoherenceError(
            f"Windows UA-CH platform is not valid for linux-chrome: {ua_ch_platform}"
        )

    renderer = _renderer_blob(persona)
    windows_hit = _RENDERER_WINDOWS_RE.search(renderer)
    if windows_hit:
        raise PersonaCoherenceError(
            f"Windows GPU renderer is not valid for linux-chrome: {windows_hit.group(0)}"
        )
    software_hit = _RENDERER_SOFTWARE_RE.search(renderer)
    if software_hit:
        raise PersonaCoherenceError(
            f"Software renderer is not valid for linux-chrome: {software_hit.group(0)}"
        )

    _require_chrome_151_desktop(persona, "linux-chrome")

    fonts = [str(f).lower() for f in (persona.get("recorded_fonts") or [])]
    if fonts and all(any(marker in font for marker in _WINDOWS_MARKER_FONTS) for font in fonts):
        raise PersonaCoherenceError(
            "Segoe/Calibri-only font list is not valid for linux-chrome"
        )


def validate_windows_chrome(persona: PersonaDict) -> None:
    """Raise ``PersonaCoherenceError`` if *persona* is not a Windows Chrome 151 desktop."""
    platform = str(persona.get("platform") or "")
    if platform.lower().startswith("linux"):
        raise PersonaCoherenceError(
            f"Linux platform is not valid for windows-chrome: {platform}"
        )
    if platform not in _WINDOWS_PLATFORMS:
        raise PersonaCoherenceError(
            f"Win32/Windows platform required for windows-chrome, got {platform!r}"
        )

    ua_ch_platform = str(persona.get("ua_ch_platform") or "")
    if ua_ch_platform.lower() == "linux":
        raise PersonaCoherenceError(
            f"Linux UA-CH platform is not valid for windows-chrome: {ua_ch_platform}"
        )
    if ua_ch_platform.lower() != "windows":
        raise PersonaCoherenceError(
            f"Windows UA-CH platform required for windows-chrome, got {ua_ch_platform!r}"
        )

    renderer = _renderer_blob(persona)
    software_hit = _RENDERER_SOFTWARE_RE.search(renderer)
    if software_hit:
        raise PersonaCoherenceError(
            f"Software renderer is not valid for windows-chrome: {software_hit.group(0)}"
        )
    mesa_hit = _RENDERER_MESA_RE.search(renderer)
    if mesa_hit:
        raise PersonaCoherenceError(
            f"Mesa/OpenGL renderer is not valid for windows-chrome: {mesa_hit.group(0)}"
        )
    if not _RENDERER_D3D_RE.search(renderer):
        raise PersonaCoherenceError(
            f"D3D11/Direct3D renderer required for windows-chrome, got {renderer!r}"
        )

    _require_chrome_151_desktop(persona, "windows-chrome")

    platform_version = str(persona.get("ua_ch_platform_version") or "")
    if platform_version not in {"10.0.0", "15.0.0"}:
        raise PersonaCoherenceError(
            "Windows UA-CH platformVersion must be 10.0.0 or 15.0.0, "
            f"got {platform_version!r}"
        )

    recorded = [str(f).lower() for f in (persona.get("recorded_fonts") or [])]
    families = [str(f).lower() for f in (persona.get("font_families") or [])]
    if not any("segoe" in font for font in (*recorded, *families)):
        raise PersonaCoherenceError(
            "Segoe font required for windows-chrome (recorded_fonts or pack-backed font_families)"
        )


def validate_persona(persona: PersonaDict) -> None:
    """Alias used by PERSONA-DATA.md."""
    validate_linux_chrome(persona)
