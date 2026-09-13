"""Apply GeoIP timezone / locale / WebRTC IP after sampling.

Does not re-run OS/GPU coherence rules — an explicit GeoIP locale vs the
sampled Accept-Language is intended. Explicit timezone=/locale=/raw flags
are resolved before this overlay (see ``maybe_resolve_geoip``).
"""

from __future__ import annotations

from .schema import PersonaDict


def apply_geoip(
    persona: PersonaDict,
    timezone: str | None = None,
    locale: str | None = None,
    exit_ip: str | None = None,
) -> PersonaDict:
    """Mutate only tz / languages / WebRTC fields. Hardware and screen stay put."""
    if timezone:
        persona["timezone_id"] = timezone
    if locale:
        persona["languages"] = languages_from_locale(locale)
    if exit_ip:
        persona["webrtc_mask_ip"] = exit_ip
        persona["mask_webrtc_host_candidates"] = True
    return persona


def languages_from_locale(locale: str) -> list[str]:
    """Navigator / Accept-Language list for a BCP 47 tag.

    Region English (``en-PK``) keeps the region tag first, then the Chrome
    pack Chromium will actually load (``en-GB``), then the language.
    ``de-DE`` stays ``["de-DE", "de"]``.
    """
    from ..geoip import chrome_lang_for_locale

    languages: list[str] = [locale]
    chrome_lang = chrome_lang_for_locale(locale)
    if chrome_lang and chrome_lang not in languages:
        languages.append(chrome_lang)
    if "-" in locale:
        base = locale.split("-", 1)[0]
        if base not in languages:
            languages.append(base)
    return languages
