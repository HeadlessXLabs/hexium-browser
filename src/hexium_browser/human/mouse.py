"""hexium_browser-human — Human-like mouse movement and clicking."""

from __future__ import annotations

import math
import random
from typing import Protocol, Tuple

from .config import HumanConfig, rand, rand_range, sleep_ms

_DEFAULT_TARGET_WIDTH = 100.0
_MIN_SPREAD = 2.0
_MAX_SPREAD = 200.0
_MIN_STEPS = 25


class RawMouse(Protocol):
    def move(self, x: float, y: float) -> None: ...
    def down(self) -> None: ...
    def up(self) -> None: ...
    def wheel(self, delta_x: float, delta_y: float) -> None: ...


class Point:
    __slots__ = ("x", "y")
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _bezier(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    u = 1 - t
    uu = u * u
    uuu = uu * u
    tt = t * t
    ttt = tt * t
    return Point(
        uuu * p0.x + 3 * uu * t * p1.x + 3 * u * tt * p2.x + ttt * p3.x,
        uuu * p0.y + 3 * uu * t * p1.y + 3 * u * tt * p2.y + ttt * p3.y,
    )


def _resolved_width(target_width: float | None) -> float:
    if target_width is None or target_width <= 0:
        return _DEFAULT_TARGET_WIDTH
    return float(target_width)


def _pt_add(a: Point, b: Point) -> Point:
    return Point(a.x + b.x, a.y + b.y)


def _pt_sub(a: Point, b: Point) -> Point:
    return Point(a.x - b.x, a.y - b.y)


def _pt_mult(a: Point, s: float) -> Point:
    return Point(a.x * s, a.y * s)


def _pt_mag(a: Point) -> float:
    return math.hypot(a.x, a.y)


def _pt_unit(a: Point) -> Point:
    mag = _pt_mag(a)
    if mag < 1e-9:
        return Point(0.0, 0.0)
    return _pt_mult(a, 1.0 / mag)


def _pt_perp(a: Point) -> Point:
    return Point(a.y, -a.x)


def _set_magnitude(a: Point, amount: float) -> Point:
    return _pt_mult(_pt_unit(a), amount)


def _random_on_line(a: Point, b: Point) -> Point:
    return _pt_add(a, _pt_mult(_pt_sub(b, a), random.random()))


def generate_bezier_anchors(start: Point, end: Point, spread: float) -> Tuple[Point, Point]:
    """Ghost-cursor same-side knots (Xetera). Sorted along the chord, not by x."""
    side = 1.0 if round(random.random()) == 1 else -1.0

    def _one() -> Point:
        rand_mid = _random_on_line(start, end)
        along = _pt_sub(rand_mid, start)
        if _pt_mag(along) < 1e-9:
            along = _pt_sub(end, start)
        normal = _set_magnitude(_pt_perp(along), spread)
        choice = _pt_mult(normal, side)
        return _random_on_line(rand_mid, _pt_add(rand_mid, choice))

    a1, a2 = _one(), _one()
    dx = end.x - start.x
    dy = end.y - start.y

    def _proj(p: Point) -> float:
        return (p.x - start.x) * dx + (p.y - start.y) * dy

    if _proj(a1) > _proj(a2):
        a1, a2 = a2, a1
    return a1, a2


def should_overshoot(dist: float, threshold: float) -> bool:
    return dist > threshold


def overshoot_point(dest: Point, radius: float) -> Point:
    angle = random.random() * 2 * math.pi
    rad = radius * math.sqrt(random.random())
    return Point(dest.x + rad * math.cos(angle), dest.y + rad * math.sin(angle))


def _bezier_speed(t: float, p0: Point, p1: Point, p2: Point, p3: Point) -> float:
    u = 1.0 - t
    b1 = 3 * u * u * (p1.x - p0.x) + 6 * u * t * (p2.x - p1.x) + 3 * t * t * (p3.x - p2.x)
    b2 = 3 * u * u * (p1.y - p0.y) + 6 * u * t * (p2.y - p1.y) + 3 * t * t * (p3.y - p2.y)
    return math.hypot(b1, b2)


def _polyline_length(pts: list[Point]) -> float:
    total = 0.0
    for i in range(1, len(pts)):
        total += math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y)
    return total


def _ghost_step_count(length: float, width: float, cfg: HumanConfig) -> int:
    speed = random.random()
    base_time = speed * _MIN_STEPS
    fitts = 2.0 * math.log2(length / width + 1.0)
    steps = math.ceil((math.log2(fitts + 1.0) + base_time) * 3.0)
    return max(int(_clamp(steps, cfg.mouse_min_steps, cfg.mouse_max_steps)), 2)


def path(
    start: Point,
    end: Point,
    cfg: HumanConfig | None = None,
    *,
    target_width: float | None = None,
    spread_override: float | None = None,
) -> list[Point]:
    """Ghost-cursor cubic LUT: same-side anchors, Fitts step count, Gaussian jitter."""
    dx = end.x - start.x
    dy = end.y - start.y
    dist = math.hypot(dx, dy)
    if dist < 1e-9:
        return [Point(end.x, end.y)]

    if cfg is None:
        from .config import HumanConfig as _HC
        cfg = _HC()
    sigma = cfg.mouse_jitter_sigma
    width = _resolved_width(target_width)
    spread = (
        float(spread_override)
        if spread_override is not None
        else _clamp(dist, _MIN_SPREAD, _MAX_SPREAD)
    )
    cp1, cp2 = generate_bezier_anchors(start, end, spread)

    probe = 24
    probe_pts = [_bezier(start, cp1, cp2, end, i / (probe - 1)) for i in range(probe)]
    length = _polyline_length(probe_pts) * 0.8
    steps = _ghost_step_count(max(length, dist * 0.8), width, cfg)

    last_i = steps - 1
    pts: list[Point] = []
    for i in range(steps):
        t = i / last_i
        pt = _bezier(start, cp1, cp2, end, t)
        if 0 < i < last_i and sigma > 0:
            pt = Point(pt.x + random.gauss(0.0, sigma), pt.y + random.gauss(0.0, sigma))
        pts.append(pt)
    pts[0] = Point(start.x, start.y)
    pts[-1] = Point(end.x, end.y)
    return pts


def _timestamp_delays_ms(pts: list[Point], speed: float) -> list[float]:
    """Ghost-cursor generateTimestamps — trapezoid of |B'| between LUT knots."""
    n = len(pts)
    if n <= 1:
        return []
    delays: list[float] = []

    def _time_to_move(p0: Point, p1: Point, p2: Point, p3: Point) -> float:
        total = 0.0
        dt = 1.0 / n
        t = 0.0
        while t < 1.0:
            v1 = _bezier_speed(t * dt, p0, p1, p2, p3)
            v2 = _bezier_speed(t, p0, p1, p2, p3)
            total += (v1 + v2) * dt / 2.0
            t += dt
        return total / max(speed, 1e-6)

    for i in range(1, n):
        p0 = pts[i - 1]
        p1 = pts[i]
        p2 = pts[i + 1] if i + 1 < n else _pt_add(p1, _pt_sub(p1, p0))
        p3 = pts[i + 2] if i + 2 < n else _pt_add(p2, _pt_sub(p2, p1))
        delays.append(max(0.0, _time_to_move(p0, p1, p2, p3)))
    return delays


def _fitts_duration_s(dist: float, width: float, cfg: HumanConfig) -> float:
    mt = cfg.mouse_fitts_a + cfg.mouse_fitts_b * math.log2(dist / width + 1.0)
    mt *= random.uniform(0.85, 1.15)
    return max(0.05, mt)


def _scale_delays(delays: list[float], duration_s: float, max_time_s: float) -> list[float]:
    if not delays:
        return delays
    total_s = sum(delays) / 1000.0
    target = min(max(duration_s, 0.08), max_time_s)
    if total_s < 1e-6:
        even = (target / len(delays)) * 1000.0
        return [even] * len(delays)
    scale = target / total_s
    return [d * scale for d in delays]


def plan_mouse_move(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    cfg: HumanConfig,
    target_width: float | None = None,
) -> tuple[list[Point], list[float]]:
    """Points + ghost-cursor timestamp delays (ms), capped at mouse_max_time_s."""
    start = Point(start_x, start_y)
    end = Point(end_x, end_y)
    dist = math.hypot(end_x - start_x, end_y - start_y)
    pts = _compose_move_points(start, end, cfg, target_width)
    width = _resolved_width(target_width)
    speed = random.uniform(0.5, 1.0)
    delays = _timestamp_delays_ms(pts, speed)
    mt = _fitts_duration_s(max(dist, 1e-9), width, cfg)
    delays = _scale_delays(delays, mt, cfg.mouse_max_time_s)
    return pts, delays


def _compose_move_points(
    start: Point,
    end: Point,
    cfg: HumanConfig,
    target_width: float | None,
) -> list[Point]:
    dist = math.hypot(end.x - start.x, end.y - start.y)
    if dist < 1:
        return [Point(end.x, end.y)]
    width = _resolved_width(target_width)
    if should_overshoot(dist, cfg.mouse_overshoot_threshold):
        mid = overshoot_point(end, cfg.mouse_overshoot_radius)
        first = path(start, mid, cfg, target_width=width)
        second = path(
            mid,
            end,
            cfg,
            target_width=width,
            spread_override=cfg.mouse_overshoot_spread,
        )
        return first + second[1:]
    return path(start, end, cfg, target_width=width)


def human_move(
    raw: RawMouse,
    start_x: float, start_y: float,
    end_x: float, end_y: float,
    cfg: HumanConfig,
    target_width: float | None = None,
) -> None:
    pts, delays = plan_mouse_move(
        start_x, start_y, end_x, end_y, cfg, target_width=target_width,
    )
    for i, pt in enumerate(pts):
        raw.move(round(pt.x), round(pt.y))
        if i < len(delays):
            sleep_ms(delays[i])


def click_target(box: dict, is_input: bool, cfg: HumanConfig) -> Point:
    if is_input:
        x_frac = rand_range(cfg.click_input_x_range)
        y_frac = rand(0.30, 0.70)
    else:
        pad = _clamp(cfg.mouse_click_padding / 100.0, 0.0, 1.0)
        lo = pad / 2.0
        hi = 1.0 - pad / 2.0
        if hi < lo:
            lo, hi = 0.5, 0.5
        x_frac = rand(lo, hi)
        y_frac = rand(lo, hi)
    return Point(round(box["x"] + box["width"] * x_frac),
                 round(box["y"] + box["height"] * y_frac))


def human_click(raw: RawMouse, is_input: bool, cfg: HumanConfig) -> None:
    aim_delay = rand_range(cfg.click_aim_delay_input) if is_input else rand_range(cfg.click_aim_delay_button)
    sleep_ms(aim_delay)
    hold_time = rand_range(cfg.click_hold_input) if is_input else rand_range(cfg.click_hold_button)
    raw.down()
    sleep_ms(hold_time)
    raw.up()


def human_idle(raw: RawMouse, seconds: float, cx: float, cy: float, cfg: HumanConfig) -> None:
    import time as _time
    end_time = _time.monotonic() + seconds
    x, y = cx, cy
    while _time.monotonic() < end_time:
        dx = (random.random() - 0.5) * 2 * cfg.idle_drift_px
        dy = (random.random() - 0.5) * 2 * cfg.idle_drift_px
        x += dx
        y += dy
        raw.move(round(x), round(y))
        sleep_ms(rand_range(cfg.idle_pause_range))
