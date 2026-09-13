"""HexiumPersona JSON field names — keep in sync with hexium_persona.h."""

from __future__ import annotations

from typing import TypedDict

# Frozen Chrome version the engine ships (HX-P0-03b). Network datapoints lag Stable.
CHROME_UA_VERSION = "151.0.7922.174"

# Packed header network lags Stable (clusters through ~147, no 151 rows).
# Sample majors at or above this floor, then rewrite to CHROME_UA_VERSION.
MIN_SAMPLED_CHROME_MAJOR = 140
MAX_HARDWARE_CONCURRENCY = 32

# FNV-1a 64-bit — same constants as HashSeedString in hexium_persona.cc.
_FNV_OFFSET = 0xCBF29CE484222325
_FNV_PRIME = 0x100000001B3
_SEED_FALLBACK = 0x485845494D5F3135

# Desktop Chrome 151 leaves UA-CH `model` empty. Do not invent OEM names
# (ThinkPad + RTX 3080 is a Pixelscan inconsistency).
LINUX_DESKTOP_MODELS = (
    "Dell Inc. OptiPlex 7090",
    "HP EliteDesk 800 G6",
    "Lenovo ThinkCentre M70q",
    "Dell Inc. Precision 3650",
    "HP ProDesk 600 G6",
)

WINDOWS_DESKTOP_MODELS = (
    "Dell Inc. XPS 15 9520",
    "HP EliteBook 840 G8",
    "Lenovo ThinkPad X1 Carbon Gen 9",
    "Dell Inc. Latitude 5420",
    "HP ProBook 450 G8",
)

# Keys the engine JSON loader understands (HexiumPersona). Linux omits GPU/fonts;
# Windows includes them so ShouldSpoofFingerprint() can apply D3D + Segoe.
ENGINE_JSON_KEYS = (
    "seed",
    "user_agent_product",
    "platform",
    "ua_ch_platform",
    "ua_ch_model",
    "ua_ch_platform_version",
    "languages",
    "timezone_id",
    "screen_width",
    "screen_height",
    "screen_avail_width",
    "screen_avail_height",
    "color_depth",
    "device_pixel_ratio",
    "outer_height_delta",
    "hardware_concurrency",
    "device_memory_gb",
    "audio_sample_rate",
    "use_native_surfaces",
    "spoofing_enabled",
    "mask_webrtc_host_candidates",
    "webrtc_mask_ip",
    "webgl_vendor",
    "webgl_renderer",
    "webgpu_vendor",
    "webgpu_architecture",
    "font_families",
    "system_ui_font",
)

# Linux chrome-on-Linux: never send spoof GPU/fonts even if present on the dict.
LINUX_ENGINE_OMIT_KEYS = (
    "webgl_vendor",
    "webgl_renderer",
    "webgpu_vendor",
    "webgpu_architecture",
    "font_families",
    "system_ui_font",
)

# Wrapper-only keys — recorded for diagnostics, never sent as spoof GPU/fonts.
RECORDED_KEYS = (
    "user_agent",
    "ua_ch_full_version",
    "ua_ch_full_version_list",
    "ua_ch_brands",
    "ua_ch_platform_version",
    "recorded_webgl_vendor",
    "recorded_webgl_renderer",
    "recorded_fonts",
)

# Same whitelist as PopulateWindowsSurfaceDefaults (engine). Lowercase for
# IsFontFamilyAllowed.
WINDOWS_FONT_FAMILIES = (
    "arial",
    "arial black",
    "bahnschrift",
    "calibri",
    "cambria",
    "cambria math",
    "candara",
    "comic sans ms",
    "consolas",
    "constantia",
    "corbel",
    "courier new",
    "ebrima",
    "franklin gothic medium",
    "gabriola",
    "gadugi",
    "georgia",
    "impact",
    "ink free",
    "javanese text",
    "leelawadee ui",
    "lucida console",
    "lucida sans unicode",
    "malgun gothic",
    "marlett",
    "microsoft himalaya",
    "microsoft jhenghei",
    "microsoft new tai lue",
    "microsoft phagspa",
    "microsoft sans serif",
    "microsoft tai le",
    "microsoft yahei",
    "microsoft yi baiti",
    "mingliu-extb",
    "mongolian baiti",
    "ms gothic",
    "mv boli",
    "myanmar text",
    "nirmala ui",
    "palatino linotype",
    "segoe mdl2 assets",
    "segoe print",
    "segoe script",
    "segoe ui",
    "segoe ui emoji",
    "segoe ui historic",
    "segoe ui symbol",
    "simsun-extb",
    "sylfaen",
    "symbol",
    "tahoma",
    "times new roman",
    "trebuchet ms",
    "verdana",
    "webdings",
    "wingdings",
    "yu gothic",
)


class PersonaDict(TypedDict, total=False):
    seed: int
    fingerprint_seed: str
    user_agent_product: str
    platform: str
    ua_ch_platform: str
    ua_ch_model: str
    languages: list[str]
    timezone_id: str
    screen_width: int
    screen_height: int
    screen_avail_width: int
    screen_avail_height: int
    color_depth: int
    device_pixel_ratio: float
    outer_height_delta: int
    hardware_concurrency: int
    device_memory_gb: float
    audio_sample_rate: float
    use_native_surfaces: bool
    spoofing_enabled: bool
    mask_webrtc_host_candidates: bool
    webrtc_mask_ip: str
    user_agent: str
    ua_ch_full_version: str
    ua_ch_full_version_list: list[dict]
    ua_ch_brands: list[dict]
    ua_ch_platform_version: str
    recorded_webgl_vendor: str
    recorded_webgl_renderer: str
    recorded_fonts: list[str]
    webgl_vendor: str
    webgl_renderer: str
    webgpu_vendor: str
    webgpu_architecture: str
    font_families: list[str]
    system_ui_font: str


def hash_seed_string(seed_str: str) -> int:
    """Match engine ``HashSeedString`` (FNV-1a 64-bit)."""
    h = _FNV_OFFSET
    for byte in seed_str.encode("utf-8"):
        h ^= byte
        h = (h * _FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
    return h if h else _SEED_FALLBACK
