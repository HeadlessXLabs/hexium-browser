"""Camoufox-style cursor highlighter — operator UX for CDP mouse.

Playwright never moves the OS cursor. This is a ``div`` ring (same idea as
Camoufox ``#cursor-highlighter`` in ``browser-init.patch``): 10px circle,
concentric glow, ``pointer-events: none``. No SVG, no custom OS pointer, no
``cursor: none``. Page JS still sees a DOM node; pass ``show_cursor=False`` on
stealth oracles. Humanize itself is real ``mousemove`` events.
"""

from __future__ import annotations

import logging
from typing import Any

from .config import HumanConfig

logger = logging.getLogger("hexium_browser.human.cursor")

# Camoufox chrome highlighter uses rgba(255,105,105,…) rings. Hexium demos
# use the same geometry with the blue from examples/assets/cursor_highlighter.js.
_HIGHLIGHTER_RGB = "59, 130, 246"

HIGHLIGHTER_INIT_SCRIPT = f"""
(() => {{
  if (document.getElementById("hexium-cursor-highlighter")) return;

  const el = document.createElement("div");
  el.id = "hexium-cursor-highlighter";
  el.setAttribute("aria-hidden", "true");
  el.style.cssText = [
    "position:fixed",
    "left:0",
    "top:0",
    "width:10px",
    "height:10px",
    "background-color:rgba({_HIGHLIGHTER_RGB},0.9)",
    "border-radius:50%",
    "pointer-events:none",
    "z-index:2147483647",
    "transform:translate(-50%,-50%)",
    "box-shadow:0 0 0 5px rgba({_HIGHLIGHTER_RGB},0.5),"
      + "0 0 0 10px rgba({_HIGHLIGHTER_RGB},0.3),"
      + "0 0 0 15px rgba({_HIGHLIGHTER_RGB},0.12)",
  ].join(";");

  function mount() {{
    const root = document.body || document.documentElement;
    if (root && !document.getElementById("hexium-cursor-highlighter")) {{
      root.appendChild(el);
    }}
  }}

  function onMove(e) {{
    mount();
    el.style.left = e.clientX + "px";
    el.style.top = e.clientY + "px";
  }}

  window.addEventListener("mousemove", onMove, true);
  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", mount, {{ once: true }});
  }} else {{
    mount();
  }}
}})();
""".strip()


def get_cursor_init_script(cfg: HumanConfig) -> str:
    del cfg
    return HIGHLIGHTER_INIT_SCRIPT


def _cdp_session_sync(page: Any) -> Any | None:
    stealth = getattr(page, "_stealth_world", None)
    if stealth is None:
        return None
    try:
        return stealth.get_cdp_session()
    except Exception:
        return None


async def _cdp_session_async(page: Any) -> Any | None:
    stealth = getattr(page, "_stealth_world", None)
    if stealth is None:
        return None
    try:
        return await stealth.get_cdp_session()
    except Exception:
        return None


def _runtime_evaluate_main_sync(page: Any, expression: str) -> None:
    session = _cdp_session_sync(page)
    if session is not None:
        try:
            session.send("Runtime.evaluate", {"expression": expression})
            return
        except Exception as exc:
            logger.debug("cursor highlighter CDP evaluate failed: %s", exc)
    try:
        page.evaluate(expression)
    except Exception:
        pass


async def _runtime_evaluate_main_async(page: Any, expression: str) -> None:
    session = await _cdp_session_async(page)
    if session is not None:
        try:
            await session.send("Runtime.evaluate", {"expression": expression})
            return
        except Exception as exc:
            logger.debug("cursor highlighter CDP evaluate failed: %s", exc)
    try:
        await page.evaluate(expression)
    except Exception:
        pass


def install_cursor_overlay_sync(page: Any, cfg: HumanConfig) -> None:
    if not cfg.show_cursor_overlay:
        return
    script = get_cursor_init_script(cfg)
    try:
        page.add_init_script(script)
    except Exception as exc:
        logger.debug("Could not add cursor highlighter init script: %s", exc)
    _runtime_evaluate_main_sync(page, script)


async def install_cursor_overlay_async(page: Any, cfg: HumanConfig) -> None:
    if not cfg.show_cursor_overlay:
        return
    script = get_cursor_init_script(cfg)
    try:
        await page.add_init_script(script)
    except Exception as exc:
        logger.debug("Could not add cursor highlighter init script: %s", exc)
    await _runtime_evaluate_main_async(page, script)


def attach_cursor_overlay_sync(
    page: Any,
    cfg: HumanConfig,
    raw_mouse: Any,
    cursor: Any,
) -> None:
    del raw_mouse, cursor
    if not cfg.show_cursor_overlay:
        return
    install_cursor_overlay_sync(page, cfg)


def wrap_cursor_overlay_async(
    page: Any,
    cfg: HumanConfig,
    raw_mouse: Any,
    cursor: Any,
) -> None:
    del cursor
    if not cfg.show_cursor_overlay:
        return

    orig_move = None
    try:
        orig_move = raw_mouse.move
    except Exception:
        orig_move = None

    installed = False

    async def _ensure_installed() -> None:
        nonlocal installed
        if installed:
            return
        await install_cursor_overlay_async(page, cfg)
        installed = True

    if orig_move is None:
        return

    async def move(*args: Any, **kwargs: Any) -> Any:
        await _ensure_installed()
        return await orig_move(*args, **kwargs)

    raw_mouse.move = move  # type: ignore[method-assign]
