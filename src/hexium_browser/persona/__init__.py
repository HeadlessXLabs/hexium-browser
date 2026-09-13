"""Linux and Windows Chrome 151 persona sampling (Architecture B — wrapper half).

Sample in-tree, coerce to HexiumPersona JSON, apply in C++ only.
Never JS injectors / ``addInitScript``. Linux default is ``linux-native``;
Windows ``windows-native``; macOS ``macos-native``. Pass ``windows-chrome``
or ``linux-chrome`` to sample.
"""

from __future__ import annotations

from .coerce import coerce_fingerprint, load_persona_json, to_engine_json, write_persona_json
from .fonts import WindowsFontPackError
from .geo_overlay import apply_geoip
from .rewrite_ua import rewrite_chrome_version
from .sample import sample_linux_chrome, sample_windows_chrome
from .schema import CHROME_UA_VERSION, PersonaDict, hash_seed_string
from .validate import (
    PersonaCoherenceError,
    validate_linux_chrome,
    validate_persona,
    validate_windows_chrome,
)

__all__ = [
    "CHROME_UA_VERSION",
    "PersonaCoherenceError",
    "PersonaDict",
    "apply_geoip",
    "coerce_fingerprint",
    "load_persona_json",
    "rewrite_chrome_version",
    "sample_linux_chrome",
    "sample_windows_chrome",
    "to_engine_json",
    "validate_linux_chrome",
    "validate_persona",
    "validate_windows_chrome",
    "WindowsFontPackError",
    "write_persona_json",
]
