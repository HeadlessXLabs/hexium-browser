"""Map a sampled Hexium device row onto HexiumPersona JSON fields."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .rewrite_ua import clamp_windows_ua_ch_platform_version, sync_windows_frozen_ua_platform_version
from .schema import (
    ENGINE_JSON_KEYS,
    LINUX_ENGINE_OMIT_KEYS,
    PersonaDict,
    WINDOWS_FONT_FAMILIES,
    hash_seed_string,
)

_DEFAULT_AUDIO_SAMPLE_RATE = 48000.0
_DEFAULT_TIMEZONE = "UTC"
_DEFAULT_OUTER_HEIGHT_DELTA = 88


def coerce_fingerprint(fp: Any, seed: str) -> PersonaDict:
    """Convert a sampled device row (dataclass or dict) to ``PersonaDict``.

    WebGL / fonts are always recorded. Linux omits those fields from engine JSON.
    Windows copies them into ``webgl_*`` / ``font_families`` with
    ``use_native_surfaces=false``.
    """
    data = _as_mapping(fp)
    nav = _as_mapping(data.get("navigator"))
    screen = _as_mapping(data.get("screen"))
    uad = _as_mapping(nav.get("userAgentData"))
    video = _as_mapping(data.get("videoCard"))

    ua = str(nav.get("userAgent") or data.get("user_agent") or "")
    platform = str(nav.get("platform") or "Linux x86_64")
    seed_hash = hash_seed_string(seed)
    windows = _is_windows_platform(platform, str(uad.get("platform") or ""))

    inner_h = _int(screen.get("innerHeight"), 0)
    outer_h = _int(screen.get("outerHeight"), 0)
    if outer_h > inner_h > 0:
        outer_delta = outer_h - inner_h
    else:
        height = _int(screen.get("height"), 1080)
        avail_h = _int(screen.get("availHeight"), height)
        outer_delta = max(height - avail_h, 0) or _DEFAULT_OUTER_HEIGHT_DELTA

    languages = nav.get("languages") or ["en-US", "en"]
    if isinstance(languages, str):
        languages = [languages]

    memory = nav.get("deviceMemory")
    if memory is None:
        memory = 8

    persona: PersonaDict = {
        "seed": seed_hash,
        "fingerprint_seed": seed,
        "user_agent_product": "Chrome" if "Chrome/" in ua else str(nav.get("appName") or ""),
        "platform": platform,
        "ua_ch_platform": str(uad.get("platform") or _ua_ch_platform_from(platform)),
        # Desktop Chrome: Client Hints ``model`` is empty (never a phone model).
        "ua_ch_model": "",
        "languages": [str(item) for item in languages],
        "timezone_id": _DEFAULT_TIMEZONE,
        "screen_width": _int(screen.get("width"), 1920),
        "screen_height": _int(screen.get("height"), 1080),
        "screen_avail_width": _int(screen.get("availWidth"), _int(screen.get("width"), 1920)),
        "screen_avail_height": _int(screen.get("availHeight"), _int(screen.get("height"), 1040)),
        "color_depth": _int(screen.get("colorDepth"), 24),
        "device_pixel_ratio": float(screen.get("devicePixelRatio") or 1.0),
        "outer_height_delta": outer_delta,
        "hardware_concurrency": _int(nav.get("hardwareConcurrency"), 8),
        "device_memory_gb": _bucket_device_memory(memory, windows=windows),
        "audio_sample_rate": _DEFAULT_AUDIO_SAMPLE_RATE,
        "use_native_surfaces": not windows,
        "spoofing_enabled": True,
        "mask_webrtc_host_candidates": False,
        "user_agent": ua,
        "ua_ch_full_version": str(uad.get("uaFullVersion") or ""),
        "ua_ch_full_version_list": [_copy_brand(item) for item in (uad.get("fullVersionList") or [])],
        "ua_ch_brands": [_copy_brand(item) for item in (uad.get("brands") or [])],
        "ua_ch_platform_version": str(uad.get("platformVersion") or ""),
        "recorded_webgl_vendor": str(video.get("vendor") or ""),
        "recorded_webgl_renderer": str(video.get("renderer") or ""),
        "recorded_fonts": [str(item) for item in (data.get("fonts") or [])],
    }
    _fix_screen_geometry(persona)
    if windows:
        _apply_windows_surfaces(persona)
        persona["ua_ch_platform_version"] = clamp_windows_ua_ch_platform_version(
            str(persona.get("ua_ch_platform_version") or "")
        )
        sync_windows_frozen_ua_platform_version(persona)
    return persona


def to_engine_json(persona: PersonaDict) -> dict[str, Any]:
    """Subset matching ``HexiumPersona``. Omits GPU/fonts on Linux."""
    windows = _is_windows_platform(
        str(persona.get("platform") or ""),
        str(persona.get("ua_ch_platform") or ""),
    )
    out: dict[str, Any] = {}
    for key in ENGINE_JSON_KEYS:
        if key not in persona:
            continue
        if not windows and key in LINUX_ENGINE_OMIT_KEYS:
            continue
        value = persona[key]
        if value is None:
            continue
        if key == "webrtc_mask_ip" and value == "":
            continue
        out[key] = value
    return out


def write_persona_json(persona: PersonaDict, user_data_dir: str | os.PathLike) -> Path:
    """Write engine JSON next to the persistent profile (not /tmp unless that *is* the profile)."""
    dest_dir = Path(os.fspath(user_data_dir))
    dest_dir.mkdir(parents=True, exist_ok=True)
    payload = to_engine_json(persona)
    fp_seed = persona.get("fingerprint_seed")
    if fp_seed:
        payload["fingerprint_seed"] = fp_seed
    dest = dest_dir / "persona.json"
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest


def load_persona_json(user_data_dir: str | os.PathLike) -> dict[str, Any] | None:
    path = Path(os.fspath(user_data_dir)) / "persona.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    if not isinstance(data, dict):
        return None
    if not data.get("fingerprint_seed") and data.get("seed") in (None, ""):
        return None
    return data


def _copy_brand(item: Any) -> dict:
    if isinstance(item, dict):
        return dict(item)
    return {"brand": str(getattr(item, "brand", item)), "version": str(getattr(item, "version", ""))}


def _is_windows_platform(platform: str, ua_ch_platform: str = "") -> bool:
    if platform in {"Win32", "Win64"} or platform.lower().startswith("win"):
        return True
    return ua_ch_platform.lower() == "windows"


def _apply_windows_surfaces(persona: PersonaDict) -> None:
    vendor = str(persona.get("recorded_webgl_vendor") or "")
    renderer = str(persona.get("recorded_webgl_renderer") or "")
    persona["webgl_vendor"] = vendor
    persona["webgl_renderer"] = renderer
    webgpu_vendor, webgpu_architecture = _webgpu_from_renderer(renderer)
    persona["webgpu_vendor"] = webgpu_vendor
    persona["webgpu_architecture"] = webgpu_architecture
    persona["font_families"] = list(WINDOWS_FONT_FAMILIES)
    persona["system_ui_font"] = "Segoe UI"
    persona["use_native_surfaces"] = False


def _bucket_device_memory(memory: Any, *, windows: bool) -> float:
    """Chrome only reports 0.25 / 0.5 / 1 / 2 / 4 / 8. Win11 desktops are not 0.5 GB."""
    try:
        value = float(memory)
    except (TypeError, ValueError):
        value = 8.0
    buckets = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
    bucket = min(buckets, key=lambda item: abs(item - value))
    if windows and bucket < 4.0:
        return 4.0
    return bucket


def _fix_screen_geometry(persona: PersonaDict) -> None:
    """Keep avail inside the screen and drop mixed physical/CSS rows.

    BrowserScan showed 2882×1922 screen vs 1264×800 avail — a datapack mix of
    device pixels and the window work area. Treat that as the CSS desktop.
    """
    width = max(1, _int(persona.get("screen_width"), 1920))
    height = max(1, _int(persona.get("screen_height"), 1080))
    avail_w = max(1, _int(persona.get("screen_avail_width"), width))
    avail_h = max(1, _int(persona.get("screen_avail_height"), height))
    delta = max(1, _int(persona.get("outer_height_delta"), _DEFAULT_OUTER_HEIGHT_DELTA))

    if avail_w > width:
        avail_w = width
    if avail_w < width * 0.7:
        width = avail_w
    if avail_h > height:
        avail_h = height
    if avail_h < height * 0.7:
        height = avail_h + delta
        avail_h = height - delta
    if avail_h >= height:
        avail_h = max(1, height - delta)
    if avail_w > width:
        avail_w = width

    persona["screen_width"] = width
    persona["screen_height"] = height
    persona["screen_avail_width"] = avail_w
    persona["screen_avail_height"] = avail_h
    persona["outer_height_delta"] = max(delta, height - avail_h)


def _webgpu_from_renderer(renderer: str) -> tuple[str, str]:
    blob = renderer.lower()
    if any(token in blob for token in ("intel", "uhd graphics", "iris")):
        return "intel", "gen12"
    if any(token in blob for token in ("amd", "radeon", "rx ")):
        return "amd", "rdna2"
    architecture = "ampere"
    if any(token in blob for token in ("gtx 16", "1660", "1650", "rtx 20", "turing")):
        architecture = "turing"
    elif any(token in blob for token in ("rtx 40", "ada")):
        architecture = "ada"
    return "nvidia", architecture


def _ua_ch_platform_from(platform: str) -> str:
    lowered = platform.lower()
    if lowered.startswith("win"):
        return "Windows"
    if lowered.startswith("mac"):
        return "macOS"
    return "Linux"


def _int(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_mapping(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    return dict(getattr(obj, "__dict__", {}) or {})
