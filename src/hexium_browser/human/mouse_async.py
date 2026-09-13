"""hexium_browser-human — Async human-like mouse movement and clicking.

Mirrors mouse.py but uses ``await`` for all Playwright calls and
``async_sleep_ms`` instead of ``sleep_ms``. Movement points come from
``plan_mouse_move`` so sync and async share the same path math.
"""

from __future__ import annotations

import random
from typing import Protocol

from .config import HumanConfig, rand, rand_range, async_sleep_ms
from .mouse import plan_mouse_move


class AsyncRawMouse(Protocol):
    async def move(self, x: float, y: float) -> None: ...
    async def down(self) -> None: ...
    async def up(self) -> None: ...
    async def wheel(self, delta_x: float, delta_y: float) -> None: ...


async def async_human_move(
    raw: AsyncRawMouse,
    start_x: float, start_y: float,
    end_x: float, end_y: float,
    cfg: HumanConfig,
    target_width: float | None = None,
) -> None:
    pts, delays = plan_mouse_move(
        start_x, start_y, end_x, end_y, cfg, target_width=target_width,
    )
    for i, pt in enumerate(pts):
        await raw.move(round(pt.x), round(pt.y))
        if i < len(delays):
            await async_sleep_ms(delays[i])


async def async_human_click(raw: AsyncRawMouse, is_input: bool, cfg: HumanConfig) -> None:
    aim_delay = rand_range(cfg.click_aim_delay_input) if is_input else rand_range(cfg.click_aim_delay_button)
    await async_sleep_ms(aim_delay)
    hold_time = rand_range(cfg.click_hold_input) if is_input else rand_range(cfg.click_hold_button)
    await raw.down()
    await async_sleep_ms(hold_time)
    await raw.up()


async def async_human_idle(raw: AsyncRawMouse, seconds: float, cx: float, cy: float, cfg: HumanConfig) -> None:
    import time as _time
    end_time = _time.monotonic() + seconds
    x, y = cx, cy
    while _time.monotonic() < end_time:
        dx = (random.random() - 0.5) * 2 * cfg.idle_drift_px
        dy = (random.random() - 0.5) * 2 * cfg.idle_drift_px
        x += dx
        y += dy
        await raw.move(round(x), round(y))
        await async_sleep_ms(rand_range(cfg.idle_pause_range))
