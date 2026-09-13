"""Rewrite UA string and UA-CH versions together (never mix majors)."""

from __future__ import annotations

import re

from .schema import PersonaDict

_CHROME_UA_RE = re.compile(r"Chrome/\d+(?:\.\d+){1,3}")
_CHROME_MAJOR_RE = re.compile(r"Chrome/(\d+)")
_CHROME_BRANDS = {"Google Chrome", "Chromium"}


def chrome_major_from_ua(ua: str) -> int | None:
    """Return the Chrome major from a UA, or None if the token is absent."""
    match = _CHROME_MAJOR_RE.search(ua or "")
    if match is None:
        return None
    return int(match.group(1))


def clamp_windows_ua_ch_platform_version(version: str | None) -> str:
    """Chrome 151 reduced Windows UA-CH: Win10 is ``10.0.0``, Win11 is ``15.0.0``.

    Never emit UniversalApiContract ``19.0.0``. Mapping:

    - major ``10`` → ``10.0.0``
    - major ``1``–``12`` except ``6`` (old Win10 contract) → ``10.0.0``
    - major ``13``+ (reduced Win11 or contract 13–19) → ``15.0.0``
    - empty / garbage / Linux kernel ``6.x`` → ``15.0.0``
    """
    raw = (version or "").strip()
    if not raw:
        return "15.0.0"
    major_s = raw.split(".", 1)[0]
    try:
        major = int(major_s)
    except ValueError:
        return "15.0.0"
    if major == 10:
        return "10.0.0"
    if major == 6:
        return "15.0.0"
    if 1 <= major <= 12:
        return "10.0.0"
    return "15.0.0"


_FROZEN_WINDOWS_NT = "Windows NT 10.0"


def sync_windows_frozen_ua_platform_version(persona: PersonaDict) -> PersonaDict:
    """Match UA-CH ``platformVersion`` to the frozen ``Windows NT 10.0`` UA token.

    Hexium (like Chrome) keeps ``Windows NT 10.0`` in the UA string. Client Hints
    must not claim Win11 ``15.0.0`` while the UA still reads Win10 — BrowserScan
    and similar parsers flag that split.
    """
    ua = str(persona.get("user_agent") or "")
    if _FROZEN_WINDOWS_NT in ua and str(persona.get("ua_ch_platform") or "").lower() == "windows":
        persona["ua_ch_platform_version"] = "10.0.0"
    return persona


def finalize_windows_persona(persona: PersonaDict) -> PersonaDict:
    """Clamp then sync Windows UA-CH platform version for engine JSON."""
    persona["ua_ch_platform_version"] = clamp_windows_ua_ch_platform_version(
        str(persona.get("ua_ch_platform_version") or "")
    )
    return sync_windows_frozen_ua_platform_version(persona)


def rewrite_chrome_version(persona: PersonaDict, version: str) -> PersonaDict:
    """Set Chrome UA + ``fullVersionList`` / ``uaFullVersion`` to *version* together."""
    ua = persona.get("user_agent") or ""
    persona["user_agent"] = _CHROME_UA_RE.sub(f"Chrome/{version}", ua, count=1)
    persona["ua_ch_full_version"] = version

    full_list = persona.get("ua_ch_full_version_list") or []
    persona["ua_ch_full_version_list"] = [
        {**item, "version": version} if item.get("brand") in _CHROME_BRANDS else dict(item)
        for item in full_list
    ]

    brands = persona.get("ua_ch_brands") or []
    if brands:
        major = version.split(".", 1)[0]
        persona["ua_ch_brands"] = [
            {**item, "version": major} if item.get("brand") in _CHROME_BRANDS else dict(item)
            for item in brands
        ]
    return persona
