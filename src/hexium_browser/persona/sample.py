"""Sample Linux or Windows Chrome desktop rows from the in-tree Hexium network.

The engine applies the JSON. This module only samples + coerces.
"""

from __future__ import annotations

import random
from dataclasses import asdict, is_dataclass
from typing import Any

from .coerce import coerce_fingerprint
from .rewrite_ua import chrome_major_from_ua, rewrite_chrome_version
from .schema import (
    CHROME_UA_VERSION,
    MAX_HARDWARE_CONCURRENCY,
    MIN_DESKTOP_DEVICE_MEMORY_GB,
    MIN_DESKTOP_HARDWARE_CONCURRENCY,
    MIN_SAMPLED_CHROME_MAJOR,
    PersonaDict,
    hash_seed_string,
)
from .validate import PersonaCoherenceError, validate_linux_chrome, validate_windows_chrome

MAX_DRAWS = 40

_LINUX_GENERATOR = None
_WINDOWS_GENERATOR = None


def sample_linux_chrome(seed: str) -> PersonaDict:
    """Draw a coherent Linux Chrome 151 desktop persona.

    ``seed`` is hashed into Python's RNG so the same fingerprint seed is
    deterministic across launches (hardware/screen/model). GeoIP overlay
    runs after this and may change tz/locale/WebRTC independently.
    """
    return _sample_os_chrome(
        seed,
        draw=_draw_linux_chrome,
        validate=validate_linux_chrome,
        label="Linux Chrome",
    )


def sample_windows_chrome(seed: str) -> PersonaDict:
    """Draw a coherent Windows Chrome 151 desktop persona from joint rows.

    Uses ``DeviceRowSampler(browser=chrome, os=windows, device=desktop)``.
    Chrome version is rewritten to 151 together with UA-CH; ``platformVersion``
    is clamped to Chrome 151 ``10.0.0`` (Win10) or ``15.0.0`` (Win11). GeoIP
    overlay runs after this.
    """
    return _sample_os_chrome(
        seed,
        draw=_draw_windows_chrome,
        validate=validate_windows_chrome,
        label="Windows Chrome",
    )


def _sample_os_chrome(seed: str, *, draw, validate, label: str) -> PersonaDict:
    rng_state = random.getstate()
    try:
        random.seed(hash_seed_string(seed))
        last_error: PersonaCoherenceError | None = None
        for _ in range(MAX_DRAWS):
            raw = draw()
            if not _sampled_chrome_major_ok(raw):
                continue
            persona = rewrite_chrome_version(
                coerce_fingerprint(raw, seed=seed),
                CHROME_UA_VERSION,
            )
            try:
                validate(persona)
                return persona
            except PersonaCoherenceError as exc:
                last_error = exc
        raise PersonaCoherenceError(
            f"Could not sample a coherent {label} persona after {MAX_DRAWS} draws"
        ) from last_error
    finally:
        random.setstate(rng_state)


def _draw_linux_chrome() -> dict[str, Any]:
    """One Hexium network draw: Chrome on Linux desktop, newest cluster then UA rewrite.

    Packed networks currently lag Stable (no Chrome 151 cluster). Sample the
    newest Linux Chrome desktop row; ``rewrite_chrome_version`` pins 151.
    """
    return _as_row(_linux_device_row_sampler().generate())


def _draw_windows_chrome() -> dict[str, Any]:
    """One Hexium network draw: Chrome on Windows desktop. Joints, not a grid."""
    return _as_row(_windows_device_row_sampler().generate())


def _navigator_map(raw: dict) -> dict:
    nav = raw.get("navigator")
    if isinstance(nav, dict):
        return nav
    return raw


def _sampled_chrome_major_ok(raw: dict) -> bool:
    nav = _navigator_map(raw)
    ua = str(nav.get("userAgent") or nav.get("user_agent") or "")
    major = chrome_major_from_ua(ua)
    if major is None or major < MIN_SAMPLED_CHROME_MAJOR:
        return False
    cores = nav.get("hardwareConcurrency")
    if cores is None:
        cores = raw.get("hardware_concurrency")
    try:
        cores_int = int(cores)
    except (TypeError, ValueError):
        return False
    if cores_int > MAX_HARDWARE_CONCURRENCY or cores_int < MIN_DESKTOP_HARDWARE_CONCURRENCY:
        return False
    memory = nav.get("deviceMemory")
    if memory is None:
        memory = raw.get("device_memory")
    if memory is not None:
        try:
            if float(memory) < MIN_DESKTOP_DEVICE_MEMORY_GB:
                return False
        except (TypeError, ValueError):
            return False
    return True


def _as_row(fp: Any) -> dict[str, Any]:
    if is_dataclass(fp) and not isinstance(fp, type):
        return asdict(fp)
    if isinstance(fp, dict):
        return fp
    raise TypeError(f"Unexpected device-row type: {type(fp)!r}")


def _linux_device_row_sampler():
    """Lazy singleton so unit tests that mock ``_draw_linux_chrome`` skip network load."""
    global _LINUX_GENERATOR
    if _LINUX_GENERATOR is None:
        from hexium_browser.persona.sampler import DeviceRowSampler
        from hexium_browser.persona.sampler.headers import Browser

        # Do not pin min=max=151: the zip has no 151 rows yet.
        # Newest Linux Chrome cluster + UA rewrite is the v1 path.
        chrome = Browser(name="chrome", min_version=MIN_SAMPLED_CHROME_MAJOR)
        _LINUX_GENERATOR = DeviceRowSampler(
            browser=chrome,
            os="linux",
            device="desktop",
        )
    return _LINUX_GENERATOR


def _windows_device_row_sampler():
    """Lazy singleton so unit tests that mock ``_draw_windows_chrome`` skip network load."""
    global _WINDOWS_GENERATOR
    if _WINDOWS_GENERATOR is None:
        from hexium_browser.persona.sampler import DeviceRowSampler
        from hexium_browser.persona.sampler.headers import Browser

        # Header zip lags Stable (clusters through ~147). Sample newest Windows
        # Chrome desktop row; rewrite_chrome_version pins the engine UA (151).
        chrome = Browser(name="chrome", min_version=MIN_SAMPLED_CHROME_MAJOR)
        _WINDOWS_GENERATOR = DeviceRowSampler(
            browser=chrome,
            os="windows",
            device="desktop",
        )
    return _WINDOWS_GENERATOR
