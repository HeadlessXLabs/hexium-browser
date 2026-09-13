"""hexium_browser-human — Configuration and presets.

All numeric parameters for human-like behavior are centralized here.
Two built-in presets: 'default' (normal human speed) and 'careful' (slower, more cautious).
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Literal, Tuple, TypedDict

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

Range = Tuple[float, float]
HumanPreset = Literal["default", "careful"]


class HumanConfigOverrides(TypedDict, total=False):
    typing_delay: float
    typing_delay_spread: float
    typing_pause_chance: float
    typing_pause_range: Range
    shift_down_delay: Range
    shift_up_delay: Range
    key_hold: Range
    field_switch_delay: Range
    mistype_chance: float
    mistype_delay_notice: Range
    mistype_delay_correct: Range
    mouse_min_steps: int
    mouse_max_steps: int
    mouse_overshoot_threshold: float
    mouse_overshoot_radius: float
    mouse_overshoot_spread: float
    mouse_jitter_sigma: float
    mouse_fitts_a: float
    mouse_fitts_b: float
    mouse_max_time_s: float
    mouse_click_padding: float
    click_aim_delay_input: Range
    click_aim_delay_button: Range
    click_hold_input: Range
    click_hold_button: Range
    click_input_x_range: Range
    idle_drift_px: float
    idle_pause_range: Range
    scroll_delta_base: Range
    scroll_delta_variance: float
    scroll_pause_fast: Range
    scroll_pause_slow: Range
    scroll_accel_steps: Range
    scroll_decel_steps: Range
    scroll_overshoot_chance: float
    scroll_overshoot_px: Range
    scroll_settle_delay: Range
    scroll_target_zone: Range
    scroll_pre_move_delay: Range
    initial_cursor_x: Range
    initial_cursor_y: Range
    idle_between_actions: bool
    idle_between_duration: Range
    show_cursor_overlay: bool
    cursor_preset: str
    cursor_svg: str
    cursor_hotspot_x: int
    cursor_hotspot_y: int


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------

@dataclass
class HumanConfig:
    """All tunable parameters for human-like behavior."""

    # Keyboard
    typing_delay: float = 70
    typing_delay_spread: float = 40
    typing_pause_chance: float = 0.1
    typing_pause_range: Range = (400, 1000)
    shift_down_delay: Range = (30, 70)
    shift_up_delay: Range = (20, 50)
    key_hold: Range = (15, 35)
    
    # Mistype (typo simulation)
    mistype_chance: float = 0.02
    mistype_delay_notice: Range = (100, 300)
    mistype_delay_correct: Range = (50, 150)

    field_switch_delay: Range = (800, 1500)

    # Mouse — movement
    mouse_min_steps: int = 25
    mouse_max_steps: int = 200
    mouse_overshoot_threshold: float = 500
    mouse_overshoot_radius: float = 120
    mouse_overshoot_spread: float = 10
    mouse_jitter_sigma: float = 0.5
    mouse_fitts_a: float = 0.05
    mouse_fitts_b: float = 0.12
    mouse_max_time_s: float = 1.5
    mouse_click_padding: float = 10

    # Mouse — clicks
    click_aim_delay_input: Range = (60, 140)
    click_aim_delay_button: Range = (80, 200)
    click_hold_input: Range = (40, 100)
    click_hold_button: Range = (60, 150)
    click_input_x_range: Range = (0.05, 0.30)

    # Mouse — idle
    idle_drift_px: float = 3
    idle_pause_range: Range = (300, 1000)

    # Scroll
    scroll_delta_base: Range = (80, 130)
    scroll_delta_variance: float = 0.2
    scroll_pause_fast: Range = (30, 80)
    scroll_pause_slow: Range = (80, 200)
    scroll_accel_steps: Range = (2, 3)
    scroll_decel_steps: Range = (2, 3)
    scroll_overshoot_chance: float = 0.1
    scroll_overshoot_px: Range = (50, 150)
    scroll_settle_delay: Range = (300, 600)
    scroll_target_zone: Range = (0.20, 0.80)
    scroll_pre_move_delay: Range = (100, 300)

    # Initial cursor position (as if coming from the address bar area)
    initial_cursor_x: Range = (400, 700)
    initial_cursor_y: Range = (45, 60)

    # Idle micro-movements between actions (opt-in, adds latency)
    idle_between_actions: bool = False
    idle_between_duration: Range = (0.3, 0.8)

    # Visual highlighter (headed debugging only — detectable in DOM)
    show_cursor_overlay: bool = False
    cursor_preset: str = "hexium"  # hexium | pointer | hand | ring
    cursor_svg: str = ""  # optional raw SVG; overrides preset when set
    cursor_hotspot_x: int = 3  # click point within SVG (tip of arrow)
    cursor_hotspot_y: int = 3


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

def _careful_config() -> HumanConfig:
    """Careful preset — everything slower and more deliberate."""
    return HumanConfig(
        # Keyboard — slower typing
        typing_delay=100,
        typing_delay_spread=50,
        typing_pause_chance=0.15,
        typing_pause_range=(500, 1200),
        shift_down_delay=(40, 90),
        shift_up_delay=(30, 70),
        key_hold=(20, 45),
        field_switch_delay=(1000, 2000),
        # Mouse — slower, more precise (Fitts duration ~1.4×; overshoot kept)
        mouse_fitts_a=0.07,
        mouse_fitts_b=0.168,
        mouse_max_time_s=2.0,
        # Mouse — clicks (longer aiming and holding)
        click_aim_delay_input=(80, 180),
        click_aim_delay_button=(120, 280),
        click_hold_input=(60, 140),
        click_hold_button=(80, 200),
        # Scroll — slower
        scroll_pause_fast=(100, 200),
        scroll_pause_slow=(250, 600),
        scroll_settle_delay=(400, 800),
        scroll_pre_move_delay=(150, 400),
        # Idle between actions enabled for careful preset
        idle_between_actions=True,
        idle_between_duration=(0.4, 1.0),
    )


_PRESETS: dict[str, HumanConfig] = {
    "default": HumanConfig(),
    "careful": _careful_config(),
}


def resolve_config(
    preset: HumanPreset = "default",
    overrides: HumanConfigOverrides | None = None,
) -> HumanConfig:
    """Resolve a preset name + optional overrides into a full HumanConfig.

    Args:
        preset: 'default' or 'careful'.
        overrides: Typed mapping of HumanConfig field names to override values.

    Returns:
        A new HumanConfig instance.

    Raises:
        ValueError: If preset is not a recognized name.
    """
    if preset not in _PRESETS:
        raise ValueError(
            f"Unknown humanize preset {preset!r}. "
            f"Valid presets: {', '.join(sorted(_PRESETS.keys()))}"
        )
    base = _PRESETS[preset]
    if not overrides:
        return HumanConfig(**{k: getattr(base, k) for k in base.__dataclass_fields__})
    merged = {k: getattr(base, k) for k in base.__dataclass_fields__}
    merged.update(overrides)
    return HumanConfig(**merged)


def merge_config(base: HumanConfig, overrides: dict | None) -> HumanConfig:
    """Merge ``overrides`` (a dict of HumanConfig field names → values) on top of
    ``base``. Returns a new HumanConfig — ``base`` is never mutated.

    Used by per-call overrides like ``page.type(sel, text, human_config={...})``
    so the same page can use different timings for different inputs without
    re-patching.

    Unknown keys are ignored silently to keep this forgiving for callers.
    """
    if not overrides:
        return base
    merged = {k: getattr(base, k) for k in base.__dataclass_fields__}
    for k, v in overrides.items():
        if k in base.__dataclass_fields__:
            merged[k] = v
    return HumanConfig(**merged)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def rand(lo: float, hi: float) -> float:
    """Random float in [lo, hi]."""
    return random.uniform(lo, hi)


def rand_int(lo: int, hi: int) -> int:
    """Random integer in [lo, hi] inclusive."""
    return random.randint(lo, hi)


def rand_range(r: Range) -> float:
    """Random float from a (min, max) tuple."""
    return random.uniform(r[0], r[1])


def rand_int_range(r: Range) -> int:
    """Random integer from a (min, max) tuple, inclusive."""
    return random.randint(int(r[0]), int(r[1]))


def sleep_ms(ms: float) -> None:
    """Sleep for `ms` milliseconds."""
    if ms > 0:
        time.sleep(ms / 1000.0)


async def async_sleep_ms(ms: float) -> None:
    """Async sleep for `ms` milliseconds."""
    if ms > 0:
        import asyncio
        await asyncio.sleep(ms / 1000.0)
