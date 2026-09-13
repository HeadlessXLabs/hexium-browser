"""Virtual mouse pointer — operator UX for CDP mouse (OS cursor never moves).

Looks like a normal mouse arrow, not a branded ring. Page JS still sees a
DOM node; pass ``show_cursor=False`` on stealth oracles. Humanize itself is
real ``mousemove`` events (detectable as a mouse).
"""

from __future__ import annotations

import logging
from typing import Any

from .config import HumanConfig

logger = logging.getLogger("hexium_browser.human.cursor")

# Standard Windows/Linux mouse arrow (white fill, black stroke). Hotspot = tip.
_MOUSE_POINTER = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
    'viewBox="0 0 24 24" aria-hidden="true">'
    '<path fill="#fff" stroke="#111" stroke-width="1.2" stroke-linejoin="round" '
    'd="M3.2 2.4 4 19.2l4.55-4.35 2.7 6.45 2.45-1.05-2.7-6.4L17.2 13z"/>'
    "</svg>"
)

HIGHLIGHTER_INIT_SCRIPT = f"""
(() => {{
  if (window.__hexiumCursorInstalled) return;
  window.__hexiumCursorInstalled = true;

  const style = document.createElement("style");
  style.textContent = "html, body, *, *::before, *::after {{ cursor: none !important; }}";
  (document.head || document.documentElement).appendChild(style);

  const el = document.createElement("div");
  el.setAttribute("aria-hidden", "true");
  el.style.cssText = [
    "position:fixed",
    "left:0",
    "top:0",
    "width:24px",
    "height:24px",
    "pointer-events:none",
    "z-index:2147483647",
    "filter:drop-shadow(0 1px 1px rgba(0,0,0,0.35))",
  ].join(";");
  el.innerHTML = {_MOUSE_POINTER!r};

  function mount() {{
    const root = document.body || document.documentElement;
    if (root && !el.isConnected) root.appendChild(el);
  }}

  function onMove(e) {{
    mount();
    el.style.transform = "translate(" + e.clientX + "px," + e.clientY + "px)";
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
            logger.debug("cursor pointer CDP evaluate failed: %s", exc)
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
            logger.debug("cursor pointer CDP evaluate failed: %s", exc)
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
        logger.debug("Could not add mouse pointer init script: %s", exc)
    _runtime_evaluate_main_sync(page, script)


async def install_cursor_overlay_async(page: Any, cfg: HumanConfig) -> None:
    if not cfg.show_cursor_overlay:
        return
    script = get_cursor_init_script(cfg)
    try:
        await page.add_init_script(script)
    except Exception as exc:
        logger.debug("Could not add mouse pointer init script: %s", exc)
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
