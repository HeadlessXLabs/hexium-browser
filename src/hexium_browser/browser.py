"""Core browser launch functions for hexium_browser.

Provides launch() and launch_async() — thin wrappers around Playwright
that use our patched stealth Chromium binary instead of stock Chromium.

Usage:
    from hexium_browser import launch

    browser = launch()
    page = browser.new_page()
    page.goto("https://protected-site.com")
    browser.close()
"""

from __future__ import annotations

import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any, Literal, TypedDict
from urllib.parse import quote, unquote, urlparse, urlunparse

from .config import (
    DEFAULT_VIEWPORT,
    IGNORE_DEFAULT_ARGS,
    allow_3p_cookies_enabled,
    apply_linux_headed_gui_env,
    binary_supports_headless_no_viewport,
    binary_supports_http_proxy_inline_auth,
    binary_supports_socks_proxy_inline_auth,
    binary_supports_maximized_window,
    get_default_hexium_binary_path,
    get_default_stealth_args,
    linux_headed_gui_args,
    linux_headless_gl_args,
    normalize_persona_preset,
    seed_classic_theme_prefs,
)
from .profiles import assert_persistent_profile, resolve_launch_user_data_dir
from .download import ensure_binary
from .persona.coerce import load_persona_json, write_persona_json
from .persona.fonts import WindowsFontPackError, generate_windows_fontconfig
from .persona.geo_overlay import apply_geoip
from .persona.rewrite_ua import finalize_windows_persona, rewrite_chrome_version
from .persona.sample import sample_linux_chrome, sample_windows_chrome
from .persona.schema import CHROME_UA_VERSION
from .human.config import HumanConfigOverrides, HumanPreset
from .widevine import seed_widevine_hint

logger = logging.getLogger("hexium_browser")


def _resolve_show_cursor(show_cursor: bool | None, humanize: bool) -> bool:
    """Debug ring is opt-in; humanize works without a DOM overlay."""
    del humanize
    if show_cursor is None:
        return False
    return bool(show_cursor)


def _resolve_human_config(
    human_preset: HumanPreset,
    human_config: HumanConfigOverrides | None,
    show_cursor: bool,
):
    """Merge launch-level flags into humanize config."""
    from .human.config import resolve_config

    merged = dict(human_config or {})
    merged["show_cursor_overlay"] = show_cursor
    return resolve_config(human_preset, merged)


# Sentinel to distinguish "viewport not provided" from "viewport=None" (disable emulation)
_VIEWPORT_UNSET = object()


def _default_no_viewport(browser: Any) -> None:
    """Default ``new_page()``/``new_context()`` to ``no_viewport=True``.

    ``launch()`` returns a raw Playwright ``Browser``; a bare ``browser.new_page()``
    would otherwise inherit Playwright's emulated 1280x720 viewport, producing
    ``outerWidth < innerWidth`` — a physically impossible window (bot tell). We wrap
    the two factory methods so pages track the real OS window instead. ``setdefault``
    only: an explicit ``viewport`` or ``no_viewport`` from the caller is never
    overridden (Playwright rejects passing both). Applied for headed launches only.
    Composes under humanize's ``patch_browser`` (apply this first).
    """
    orig_new_context = browser.new_context
    orig_new_page = browser.new_page

    def _patched_new_context(**kwargs: Any) -> Any:
        if "viewport" not in kwargs:
            kwargs.setdefault("no_viewport", True)
        return orig_new_context(**kwargs)

    def _patched_new_page(**kwargs: Any) -> Any:
        if "viewport" not in kwargs:
            kwargs.setdefault("no_viewport", True)
        return orig_new_page(**kwargs)

    browser.new_context = _patched_new_context
    browser.new_page = _patched_new_page


def _default_no_viewport_async(browser: Any) -> None:
    """Async variant of :func:`_default_no_viewport`."""
    orig_new_context = browser.new_context
    orig_new_page = browser.new_page

    async def _patched_new_context(**kwargs: Any) -> Any:
        if "viewport" not in kwargs:
            kwargs.setdefault("no_viewport", True)
        return await orig_new_context(**kwargs)

    async def _patched_new_page(**kwargs: Any) -> Any:
        if "viewport" not in kwargs:
            kwargs.setdefault("no_viewport", True)
        return await orig_new_page(**kwargs)

    browser.new_context = _patched_new_context
    browser.new_page = _patched_new_page


def _resolve_context_viewport(
    viewport: Any, headless: bool, headless_no_viewport: bool = False
) -> dict[str, Any]:
    """Return the viewport kwarg for a context.

    Headed: no emulated viewport so the page tracks the real window. Headless on a
    newer binary (``headless_no_viewport``): also ``no_viewport``, since it reports
    coherent dimensions without emulation. Headless on an older binary: a fixed
    ``DEFAULT_VIEWPORT`` keeps dimensions coherent and deterministic. Explicit
    ``viewport`` / ``None`` honored.
    """
    if viewport is _VIEWPORT_UNSET:
        if headless and not headless_no_viewport:
            return {"viewport": DEFAULT_VIEWPORT}
        return {"no_viewport": True}
    if viewport is None:
        return {"no_viewport": True}
    return {"viewport": viewport}


def _drop_conflicting_viewport(context_kwargs: dict[str, Any], kwargs: dict[str, Any]) -> None:
    """Playwright rejects passing both ``viewport`` and ``no_viewport``. ``viewport`` is a
    named parameter (never in ``**kwargs``), so the only conflict is a caller passing
    ``no_viewport`` via ``**kwargs`` alongside an explicit ``viewport`` — the explicit
    ``no_viewport`` wins; drop the viewport so Playwright doesn't error.
    """
    if "no_viewport" in kwargs and "viewport" in context_kwargs:
        logger.debug("Both viewport and no_viewport requested; no_viewport (kwargs) wins")
        context_kwargs.pop("viewport", None)


def _resolve_timezone(timezone: str | None, kwargs: dict[str, Any]) -> str | None:
    """Accept both timezone and timezone_id — either works, no warning."""
    if "timezone_id" in kwargs:
        if timezone is None:
            timezone = kwargs.pop("timezone_id")
        else:
            kwargs.pop("timezone_id")
    return timezone


def _check_removed_kwargs(kwargs: dict[str, Any]) -> None:
    """Raise a clear error for removed parameters that now fall into **kwargs."""
    if "backend" in kwargs:
        raise TypeError(
            "The 'backend' parameter has been removed — patchright is no longer "
            "supported and stock Playwright is the only backend. Remove the argument."
        )
    if "executable_path" in kwargs or "channel" in kwargs:
        raise TypeError(
            "Do not pass executable_path or channel. Hexium always launches the "
            "Hexium chrome binary (HEXIUM_BINARY_PATH or "
            f"{get_default_hexium_binary_path()}). Remove those arguments."
        )


_PERSISTENT_NEW_CONTEXT_ERROR = (
    "launch() opens a real Chrome profile (window + tabs). "
    "browser.new_context() would be a Playwright Incognito/CDP session. "
    "Use browser.new_page() for a new tab, or "
    "launch_persistent_context(user_data_dir) for a named profile."
)


def _is_startup_tab(page: Any) -> bool:
    """True if this is the blank window Chrome opens with a persistent profile."""
    try:
        url = page.url or ""
    except Exception:
        return False
    if url in ("", "about:blank", "chrome://newtab/", "chrome://new-tab-page/"):
        return True
    return url.startswith("chrome://new-tab-page")


def _bind_persistent_tabs(browser: Any, context: Any, *, is_async: bool = False) -> None:
    """Map Browser.new_page() to a tab on the persistent profile, not Incognito.

    Playwright's Browser.new_page() always creates a new context (OTR). Persistent
    Chrome already has a window; reuse the startup blank once, then context.new_page()
    for extra tabs.
    """
    used_startup = False
    from .human import ensure_stealth_evaluate

    for existing in list(getattr(context, "pages", []) or []):
        ensure_stealth_evaluate(existing, is_async=is_async)

    if is_async:
        orig_new_page = context.new_page
        orig_close = context.close

        async def new_page(**kwargs: Any) -> Any:
            nonlocal used_startup
            kwargs.pop("no_viewport", None)
            kwargs.pop("viewport", None)
            if not used_startup:
                pages = list(context.pages)
                if pages and _is_startup_tab(pages[0]):
                    used_startup = True
                    ensure_stealth_evaluate(pages[0], is_async=True)
                    return pages[0]
            page = await orig_new_page(**kwargs)
            ensure_stealth_evaluate(page, is_async=True)
            return page

        async def new_context(**kwargs: Any) -> Any:
            raise TypeError(_PERSISTENT_NEW_CONTEXT_ERROR)

        async def close(*, reason: str | None = None) -> None:
            if reason is None:
                await orig_close()
            else:
                await orig_close(reason=reason)

        browser.new_page = new_page
        browser.new_context = new_context
        browser.close = close
        return

    orig_new_page = context.new_page
    orig_close = context.close

    def new_page(**kwargs: Any) -> Any:
        nonlocal used_startup
        # Persistent context.new_page() does not take no_viewport/viewport
        # (those are Browser.new_page / new_context kwargs). The context
        # already launched with no_viewport=True.
        kwargs.pop("no_viewport", None)
        kwargs.pop("viewport", None)
        if not used_startup:
            pages = list(context.pages)
            if pages and _is_startup_tab(pages[0]):
                used_startup = True
                ensure_stealth_evaluate(pages[0], is_async=False)
                return pages[0]
        page = orig_new_page(**kwargs)
        ensure_stealth_evaluate(page, is_async=False)
        return page

    def new_context(**kwargs: Any) -> Any:
        raise TypeError(_PERSISTENT_NEW_CONTEXT_ERROR)

    def close(*, reason: str | None = None) -> None:
        if reason is None:
            orig_close()
        else:
            orig_close(reason=reason)

    browser.new_page = new_page
    browser.new_context = new_context
    browser.close = close


def _browser_from_persistent(context: Any) -> Any:
    browser = context.browser
    if browser is None:
        raise RuntimeError(
            "Persistent Hexium context has no browser. This Playwright build "
            "cannot drive launch() via launch_persistent_context."
        )
    return browser


def _ensure_headed_linux_env(headless: bool, kwargs: dict[str, Any]) -> None:
    """GTK_CSD=0 on headed Linux. Does not set GTK_THEME (Classic, not Adwaita)."""
    if headless:
        return
    existing = kwargs.get("env")
    merged = apply_linux_headed_gui_env(existing)
    if merged is not None:
        kwargs["env"] = merged


def _ensure_locale_env(kwargs: dict[str, Any], locale: str | None) -> None:
    """Pin LANG/LC_ALL to the Chrome language pack for *locale*.

    ``en-PK`` stays on navigator.languages; ICU/``--lang`` need ``en-GB``.
    """
    if not locale:
        return
    from .geoip import bcp47_to_posix_locale, chrome_lang_for_locale

    chrome_lang = chrome_lang_for_locale(locale) or locale
    posix = bcp47_to_posix_locale(chrome_lang)
    existing = kwargs.get("env")
    env = dict(existing) if existing is not None else dict(os.environ)
    env["LANG"] = posix
    env["LC_ALL"] = posix
    env["LANGUAGE"] = (
        f"{chrome_lang.replace('-', '_')}:{chrome_lang.split('-', 1)[0]}"
    )
    kwargs["env"] = env


def _ensure_timezone_env(kwargs: dict[str, Any], timezone: str | None) -> None:
    """Pin libc ``TZ`` to the GeoIP / ``timezone=`` IANA id.

    Blink ``Intl`` follows ``--hexium-timezone``. ``Date.toString()`` still
    reads the process timezone, so whoer shows IP tz vs "Eastern Daylight
    Time" unless ``TZ`` matches. Same pattern as ``HEXIUM_WEBRTC_MASK_IP``.
    """
    if not timezone:
        return
    os.environ["TZ"] = timezone
    existing = kwargs.get("env")
    env = dict(existing) if existing is not None else dict(os.environ)
    env["TZ"] = timezone
    kwargs["env"] = env


class _ProxySettingsRequired(TypedDict):
    server: str


class ProxySettings(_ProxySettingsRequired, total=False):
    """Playwright-compatible proxy configuration."""

    bypass: str
    username: str
    password: str


def launch(
    headless: bool = True,
    proxy: str | ProxySettings | None = None,
    args: list[str] | None = None,
    stealth_args: bool = True,
    fingerprint: str | None = None,
    timezone: str | None = None,
    locale: str | None = None,
    geoip: bool = True,
    humanize: bool = True,
    human_preset: HumanPreset = "default",
    human_config: HumanConfigOverrides | None = None,
    show_cursor: bool | None = None,
    extension_paths: list[str] | None = None,
    browser_version: str | None = None,
    user_data_dir: str | os.PathLike | None = None,
    profile: str | None = None,
    ephemeral: bool = False,
    persona: str | None = None,
    allow_3p_cookies: bool | None = None,
    _suppress_maximize: bool = False,
    **kwargs: Any,
) -> Any:
    """Launch Hexium as a real Chrome profile (window + tabs), not Incognito.

    Uses ``launch_persistent_context`` on a disk profile (never Playwright
    ``chromium.launch()`` + ``new_page()``, which is an off-the-record CDP
    context and often a /tmp tmpfs quota tell).

    ``browser.new_page()`` is a **tab**. The first call reuses Chrome's startup
    blank. Further calls open extra tabs. ``browser.new_context()`` is rejected.

    Args:
        user_data_dir: Persistent profile directory. Default: ``HEXIUM_USER_DATA_DIR``
            if set, else a new ``hexium-session-*`` folder under ``~/.hexium/profiles``.
        profile: Named profile under ``$HEXIUM_HOME/profiles`` (e.g. ``"Work"``).
        ephemeral: Force a new ``hexium-session-*`` directory (ignored when ``profile``
            or ``user_data_dir`` is set).
        persona: Linux default ``linux-native``; Windows default
            ``windows-native``; macOS default ``macos-native``. Pass
            ``windows-chrome`` or ``linux-chrome`` to sample. Alias
            ``windows-1080p`` → ``windows-chrome``, ``mac-native`` →
            ``macos-native``. A ``*-native`` name that does not match this
            OS remaps to the host native.
        allow_3p_cookies: Pass ``--hexium-allow-3p-cookies`` (HX-P4-04). Default
            off. ``True``/``False`` override ``HEXIUM_ALLOW_3P_COOKIES``.
        geoip: Map timezone, locale, and ``navigator.languages`` to the egress IP
            (proxy exit, or the machine public IP when there is no proxy). Default
            True. Pass ``geoip=False`` to opt out. Explicit ``timezone=`` /
            ``locale=`` still win. Requires ``pip install 'hexium-browser[geoip]'``.
        humanize: Human-like mouse, keys, scroll (default True).
        show_cursor: Optional blue Camoufox-style ring (debug only). Default
            ``False``. Pass ``True`` in headed demos such as
            ``humanize_click_demo.py``. Real sites: keep ``False``.
        **kwargs: Forwarded to ``launch_persistent_context``.
    """
    _check_removed_kwargs(kwargs)
    if _suppress_maximize:
        kwargs.setdefault("no_viewport", True)
    profile_path = resolve_launch_user_data_dir(
        user_data_dir, profile=profile, ephemeral=ephemeral
    )
    context = launch_persistent_context(
        profile_path,
        headless=headless,
        proxy=proxy,
        args=args,
        stealth_args=stealth_args,
        fingerprint=fingerprint,
        timezone=timezone,
        locale=locale,
        geoip=geoip,
        humanize=humanize,
        human_preset=human_preset,
        human_config=human_config,
        show_cursor=show_cursor,
        extension_paths=extension_paths,
        browser_version=browser_version,
        persona=persona,
        allow_3p_cookies=allow_3p_cookies,
        **kwargs,
    )
    browser = _browser_from_persistent(context)
    _bind_persistent_tabs(browser, context, is_async=False)
    return browser


async def launch_async(  # noqa: C901
    headless: bool = True,
    proxy: str | ProxySettings | None = None,
    args: list[str] | None = None,
    stealth_args: bool = True,
    fingerprint: str | None = None,
    timezone: str | None = None,
    locale: str | None = None,
    geoip: bool = True,
    humanize: bool = True,
    human_preset: HumanPreset = "default",
    human_config: HumanConfigOverrides | None = None,
    show_cursor: bool | None = None,
    extension_paths: list[str] | None = None,
    browser_version: str | None = None,
    user_data_dir: str | os.PathLike | None = None,
    profile: str | None = None,
    ephemeral: bool = False,
    persona: str | None = None,
    allow_3p_cookies: bool | None = None,
    _suppress_maximize: bool = False,
    **kwargs: Any,
) -> Any:
    """Async version of launch(). Real Chrome profile + tabs, not Incognito CDP.

    ``geoip`` defaults True (egress IP → timezone/locale/languages). Pass
    ``geoip=False`` to opt out; explicit ``timezone=`` / ``locale=`` still win.
    ``show_cursor`` defaults to ``False`` (pass ``True`` for headed debug demos).
    ``allow_3p_cookies`` defaults off (``HEXIUM_ALLOW_3P_COOKIES=1`` or True).
    """
    _check_removed_kwargs(kwargs)
    if _suppress_maximize:
        kwargs.setdefault("no_viewport", True)
    profile_path = resolve_launch_user_data_dir(
        user_data_dir, profile=profile, ephemeral=ephemeral
    )
    context = await launch_persistent_context_async(
        profile_path,
        headless=headless,
        proxy=proxy,
        args=args,
        stealth_args=stealth_args,
        fingerprint=fingerprint,
        timezone=timezone,
        locale=locale,
        geoip=geoip,
        humanize=humanize,
        human_preset=human_preset,
        human_config=human_config,
        show_cursor=show_cursor,
        extension_paths=extension_paths,
        browser_version=browser_version,
        persona=persona,
        allow_3p_cookies=allow_3p_cookies,
        **kwargs,
    )
    browser = _browser_from_persistent(context)
    _bind_persistent_tabs(browser, context, is_async=True)
    return browser


def launch_persistent_context(
    user_data_dir: str | os.PathLike,
    headless: bool = True,
    proxy: str | ProxySettings | None = None,
    args: list[str] | None = None,
    stealth_args: bool = True,
    fingerprint: str | None = None,
    user_agent: str | None = None,
    viewport: Any = _VIEWPORT_UNSET,
    locale: str | None = None,
    timezone: str | None = None,
    color_scheme: Literal["light", "dark", "no-preference"] | None = None,
    geoip: bool = True,
    humanize: bool = True,
    human_preset: HumanPreset = "default",
    human_config: HumanConfigOverrides | None = None,
    show_cursor: bool | None = None,
    extension_paths: list[str] | None = None,
    browser_version: str | None = None,
    persona: str | None = None,
    allow_3p_cookies: bool | None = None,
    **kwargs: Any,
) -> Any:
    """Launch stealth browser with a persistent profile and return a BrowserContext.

    This persists cookies, localStorage, cache, and other browser state across
    sessions by storing them in ``user_data_dir``. Also avoids incognito detection
    by services like BrowserScan (-10% penalty).

    Args:
        user_data_dir: Path to the directory where browser profile data is stored.
            Created automatically if it doesn't exist. Reuse the same path across
            sessions to restore cookies, localStorage, cached credentials, etc.
        headless: Run in headless mode (default True).
        proxy: Proxy URL string or Playwright proxy dict (see launch() for details).
        args: Additional Chromium CLI arguments.
        extension_paths: List of Chrome extension paths to load.
        stealth_args: Include default stealth fingerprint args (default True).
        user_agent: Custom user agent string.
        viewport: Viewport size dict, e.g. {"width": 1920, "height": 1080}.
            Pass None to disable viewport emulation (use OS window size).
        locale: Browser locale, e.g. "en-US".
        timezone: IANA timezone (e.g. 'America/New_York').
        color_scheme: Color scheme preference — 'light', 'dark', or 'no-preference'.
            Default: None (uses Chromium default, which is 'light').
        geoip: Map timezone, locale, and ``navigator.languages`` to the egress IP
            (proxy exit, or the machine public IP when there is no proxy). Default
            True. Pass ``geoip=False`` to opt out. Explicit ``timezone=`` /
            ``locale=`` still win. Requires ``pip install 'hexium-browser[geoip]'``.
        humanize: Enable human-like mouse, keyboard, scroll behavior (default True).
        human_preset: Humanize preset — 'default' or 'careful' (default 'default').
        human_config: Custom humanize config mapping to override preset values.
        show_cursor: Optional blue Camoufox-style ring (debug only). Default
            ``False``. Pass ``True`` in headed demos such as
            ``humanize_click_demo.py``. Real sites: keep ``False``.
        **kwargs: Passed directly to playwright.chromium.launch_persistent_context().

    Returns:
        Playwright BrowserContext object backed by a persistent profile.
        Call ``.close()`` when done — this also stops the Playwright instance.

    Example:
        >>> from hexium_browser import launch_persistent_context
        >>> ctx = launch_persistent_context("/data/hexium-work", headless=False)
        >>> page = ctx.new_page()
        >>> page.goto("https://protected-site.com")
        >>> ctx.close()  # Profile is saved; re-use path next run to restore state.
    """
    _check_removed_kwargs(kwargs)
    show_cursor = _resolve_show_cursor(show_cursor, humanize)
    user_data_dir = assert_persistent_profile(Path(os.fspath(user_data_dir)))

    from playwright.sync_api import sync_playwright

    timezone = _resolve_timezone(timezone, kwargs)

    binary_path = ensure_binary(browser_version=browser_version)
    timezone, locale, exit_ip = maybe_resolve_geoip(geoip, proxy, timezone, locale, args)
    proxy_kwargs, proxy_extra_args = _resolve_proxy_config(proxy, browser_version)
    args = _resolve_webrtc_args(args, proxy)
    args = _append_webrtc_exit_ip(args, exit_ip)
    chrome_args = build_args(stealth_args, (args or []) + proxy_extra_args, timezone=timezone, locale=locale, headless=headless, extension_paths=extension_paths, start_maximized=binary_supports_maximized_window(browser_version) and viewport is _VIEWPORT_UNSET and "viewport" not in kwargs and "no_viewport" not in kwargs, fingerprint=fingerprint, user_data_dir=user_data_dir, persona=persona, allow_3p_cookies=allow_3p_cookies)
    _maybe_warn_windows_fonts(chrome_args)

    logger.debug(
        "Launching persistent stealth Chromium (headless=%s, user_data_dir=%s)",
        headless,
        user_data_dir,
    )

    # locale and timezone are set via binary flags (--lang, --hexium-timezone)
    # — NOT via Playwright context kwargs which use detectable CDP emulation.
    context_kwargs: dict[str, Any] = {}
    if user_agent:
        context_kwargs["user_agent"] = user_agent
    context_kwargs.update(
        _resolve_context_viewport(
            viewport, headless, binary_supports_headless_no_viewport(browser_version)
        )
    )
    if color_scheme:
        context_kwargs["color_scheme"] = color_scheme
    context_kwargs.update(kwargs)
    _drop_conflicting_viewport(context_kwargs, kwargs)
    _ensure_headed_linux_env(headless, context_kwargs)
    _ensure_windows_fontconfig_env(context_kwargs, chrome_args, user_data_dir)
    _ensure_persona_json_env(context_kwargs, user_data_dir)
    _ensure_locale_env(context_kwargs, locale)
    _ensure_timezone_env(context_kwargs, timezone)
    _ensure_webrtc_mask_env(context_kwargs, chrome_args)

    seed_classic_theme_prefs(user_data_dir)
    seed_widevine_hint(user_data_dir, binary_path)

    pw = sync_playwright().start()
    try:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=os.fspath(user_data_dir),
            executable_path=binary_path,
            headless=headless,
            args=chrome_args,
            ignore_default_args=IGNORE_DEFAULT_ARGS,
            **proxy_kwargs,
            **context_kwargs,
        )
    except Exception:
        try:
            pw.stop()
        except Exception as stop_exc:
            logger.warning("Playwright cleanup after launch failure failed: %s", stop_exc)
        raise

    # Patch close() to also stop the Playwright instance
    _original_close = context.close

    def _close_with_cleanup(*, reason: str | None = None) -> None:
        try:
            if reason is None:
                _original_close()
            else:
                _original_close(reason=reason)
        finally:
            pw.stop()

    context.close = _close_with_cleanup


    # Human-like behavioral patching
    if humanize:
        from .human import patch_context
        cfg = _resolve_human_config(human_preset, human_config, show_cursor)
        patch_context(context, cfg)

    return context


async def launch_persistent_context_async(
    user_data_dir: str | os.PathLike,
    headless: bool = True,
    proxy: str | ProxySettings | None = None,
    args: list[str] | None = None,
    stealth_args: bool = True,
    fingerprint: str | None = None,
    user_agent: str | None = None,
    viewport: Any = _VIEWPORT_UNSET,
    locale: str | None = None,
    timezone: str | None = None,
    color_scheme: Literal["light", "dark", "no-preference"] | None = None,
    geoip: bool = True,
    humanize: bool = True,
    human_preset: HumanPreset = "default",
    human_config: HumanConfigOverrides | None = None,
    show_cursor: bool | None = None,
    extension_paths: list[str] | None = None,
    browser_version: str | None = None,
    persona: str | None = None,
    allow_3p_cookies: bool | None = None,
    **kwargs: Any,
) -> Any:
    """Async version of launch_persistent_context().

    Launch stealth browser with a persistent profile and return a BrowserContext.
    This persists cookies, localStorage, cache, and other browser state across
    sessions by storing them in ``user_data_dir``.

    Args:
        user_data_dir: Path to the directory where browser profile data is stored.
            Created automatically if it doesn't exist.
        headless: Run in headless mode (default True).
        proxy: Proxy URL string or Playwright proxy dict (see launch() for details).
        args: Additional Chromium CLI arguments.
        extension_paths: List of Chrome extension paths to load.
        stealth_args: Include default stealth fingerprint args (default True).
        user_agent: Custom user agent string.
        viewport: Viewport size dict, e.g. {"width": 1920, "height": 1080}.
            Pass None to disable viewport emulation (use OS window size).
        locale: Browser locale, e.g. "en-US".
        timezone: IANA timezone (e.g. 'America/New_York').
        color_scheme: Color scheme preference — 'light', 'dark', or 'no-preference'.
        geoip: Map timezone, locale, and ``navigator.languages`` to the egress IP
            (proxy exit, or the machine public IP when there is no proxy). Default
            True. Pass ``geoip=False`` to opt out. Explicit ``timezone=`` /
            ``locale=`` still win.
        humanize: Enable human-like mouse, keyboard, scroll behavior (default True).
        human_preset: Humanize preset — 'default' or 'careful' (default 'default').
        human_config: Custom humanize config mapping to override preset values.
        show_cursor: Optional blue Camoufox-style ring (debug only). Default
            ``False``. Pass ``True`` in headed demos such as
            ``humanize_click_demo.py``. Real sites: keep ``False``.
        **kwargs: Passed directly to playwright.chromium.launch_persistent_context().

    Returns:
        Playwright BrowserContext object backed by a persistent profile (async API).
        Call ``await .close()`` when done.

    Example:
        >>> import asyncio
        >>> from hexium_browser import launch_persistent_context_async
        >>>
        >>> async def main():
        ...     ctx = await launch_persistent_context_async("/data/hexium-work", headless=False)
        ...     page = await ctx.new_page()
        ...     await page.goto("https://protected-site.com")
        ...     await ctx.close()
        >>>
        >>> asyncio.run(main())
    """
    _check_removed_kwargs(kwargs)
    show_cursor = _resolve_show_cursor(show_cursor, humanize)
    user_data_dir = assert_persistent_profile(Path(os.fspath(user_data_dir)))

    from playwright.async_api import async_playwright

    timezone = _resolve_timezone(timezone, kwargs)

    binary_path = ensure_binary(browser_version=browser_version)
    timezone, locale, exit_ip = maybe_resolve_geoip(geoip, proxy, timezone, locale, args)
    proxy_kwargs, proxy_extra_args = _resolve_proxy_config(proxy, browser_version)
    args = _resolve_webrtc_args(args, proxy)
    args = _append_webrtc_exit_ip(args, exit_ip)
    chrome_args = build_args(stealth_args, (args or []) + proxy_extra_args, timezone=timezone, locale=locale, headless=headless, extension_paths=extension_paths, start_maximized=binary_supports_maximized_window(browser_version) and viewport is _VIEWPORT_UNSET and "viewport" not in kwargs and "no_viewport" not in kwargs, fingerprint=fingerprint, user_data_dir=user_data_dir, persona=persona, allow_3p_cookies=allow_3p_cookies)
    _maybe_warn_windows_fonts(chrome_args)

    logger.debug(
        "Launching persistent stealth Chromium async (headless=%s, user_data_dir=%s)",
        headless,
        user_data_dir,
    )

    # locale and timezone are set via binary flags (--lang, --hexium-timezone)
    # — NOT via Playwright context kwargs which use detectable CDP emulation.
    context_kwargs: dict[str, Any] = {}
    if user_agent:
        context_kwargs["user_agent"] = user_agent
    context_kwargs.update(
        _resolve_context_viewport(
            viewport, headless, binary_supports_headless_no_viewport(browser_version)
        )
    )
    if color_scheme:
        context_kwargs["color_scheme"] = color_scheme
    context_kwargs.update(kwargs)
    _drop_conflicting_viewport(context_kwargs, kwargs)
    _ensure_headed_linux_env(headless, context_kwargs)
    _ensure_windows_fontconfig_env(context_kwargs, chrome_args, user_data_dir)
    _ensure_persona_json_env(context_kwargs, user_data_dir)
    _ensure_locale_env(context_kwargs, locale)
    _ensure_timezone_env(context_kwargs, timezone)
    _ensure_webrtc_mask_env(context_kwargs, chrome_args)

    seed_classic_theme_prefs(user_data_dir)
    seed_widevine_hint(user_data_dir, binary_path)

    pw = await async_playwright().start()
    try:
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=os.fspath(user_data_dir),
            executable_path=binary_path,
            headless=headless,
            args=chrome_args,
            ignore_default_args=IGNORE_DEFAULT_ARGS,
            **proxy_kwargs,
            **context_kwargs,
        )
    except Exception:
        try:
            await pw.stop()
        except Exception as stop_exc:
            logger.warning("Playwright cleanup after launch failure failed: %s", stop_exc)
        raise

    # Patch close() to also stop the Playwright instance
    _original_close = context.close

    async def _close_with_cleanup(*, reason: str | None = None) -> None:
        try:
            if reason is None:
                await _original_close()
            else:
                await _original_close(reason=reason)
        finally:
            await pw.stop()

    context.close = _close_with_cleanup


    # Human-like behavioral patching (async variant)
    if humanize:
        from .human import patch_context_async
        cfg = _resolve_human_config(human_preset, human_config, show_cursor)
        patch_context_async(context, cfg)

    return context


def launch_context(
    headless: bool = True,
    proxy: str | ProxySettings | None = None,
    args: list[str] | None = None,
    stealth_args: bool = True,
    fingerprint: str | None = None,
    user_agent: str | None = None,
    viewport: Any = _VIEWPORT_UNSET,
    locale: str | None = None,
    timezone: str | None = None,
    color_scheme: Literal["light", "dark", "no-preference"] | None = None,
    geoip: bool = True,
    humanize: bool = True,
    human_preset: HumanPreset = "default",
    human_config: HumanConfigOverrides | None = None,
    show_cursor: bool | None = None,
    extension_paths: list[str] | None = None,
    browser_version: str | None = None,
    persona: str | None = None,
    allow_3p_cookies: bool | None = None,
    **kwargs: Any,
) -> Any:
    """Launch stealth browser and return a BrowserContext with common options pre-set.

    Convenience function that creates a browser + context in one call.
    Useful for setting user agent, viewport, locale, etc.

    Args:
        headless: Run in headless mode (default True).
        proxy: Proxy URL string or Playwright proxy dict (see launch() for details).
        args: Additional Chromium CLI arguments.
        extension_paths: List of Chrome extension paths to load.
        stealth_args: Include default stealth fingerprint args (default True).
        user_agent: Custom user agent string.
        viewport: Viewport size dict, e.g. {"width": 1920, "height": 1080}.
            Pass None to disable viewport emulation (use OS window size).
        locale: Browser locale, e.g. "en-US".
        timezone: IANA timezone (e.g. 'America/New_York').
        color_scheme: Color scheme preference — 'light', 'dark', or 'no-preference'.
            Default: None (uses Chromium default, which is 'light').
        geoip: Map timezone, locale, and ``navigator.languages`` to the egress IP
            (proxy exit, or the machine public IP when there is no proxy). Default
            True. Pass ``geoip=False`` to opt out. Explicit ``timezone=`` /
            ``locale=`` still win. This function resolves GeoIP itself, then
            calls persistent with ``geoip=False`` to avoid a second lookup.
        humanize: Enable human-like mouse, keyboard, scroll behavior (default True).
        human_preset: Humanize preset — 'default' or 'careful' (default 'default').
        human_config: Custom humanize config mapping to override preset values.
        show_cursor: Optional blue Camoufox-style ring (debug only). Default
            ``False``. Pass ``True`` in headed demos such as
            ``humanize_click_demo.py``. Real sites: keep ``False``.
        **kwargs: Passed to browser.new_context().

    Returns:
        Playwright BrowserContext object (real profile, not Incognito).
    """
    _check_removed_kwargs(kwargs)

    timezone = _resolve_timezone(timezone, kwargs)
    timezone, locale, exit_ip = maybe_resolve_geoip(geoip, proxy, timezone, locale, args)
    args = _append_webrtc_exit_ip(args, exit_ip)
    user_data_dir = kwargs.pop("user_data_dir", None)
    profile_name = kwargs.pop("profile", None)
    ephemeral = kwargs.pop("ephemeral", False)
    profile_path = resolve_launch_user_data_dir(
        user_data_dir, profile=profile_name, ephemeral=ephemeral
    )
    return launch_persistent_context(
        profile_path,
        headless=headless,
        proxy=proxy,
        args=args,
        stealth_args=stealth_args,
        fingerprint=fingerprint,
        user_agent=user_agent,
        viewport=viewport,
        locale=locale,
        timezone=timezone,
        color_scheme=color_scheme,
        geoip=False,
        humanize=humanize,
        human_preset=human_preset,
        human_config=human_config,
        show_cursor=show_cursor,
        extension_paths=extension_paths,
        browser_version=browser_version,
        persona=persona,
        allow_3p_cookies=allow_3p_cookies,
        **kwargs,
    )


async def launch_context_async(
    headless: bool = True,
    proxy: str | ProxySettings | None = None,
    args: list[str] | None = None,
    stealth_args: bool = True,
    fingerprint: str | None = None,
    user_agent: str | None = None,
    viewport: Any = _VIEWPORT_UNSET,
    locale: str | None = None,
    timezone: str | None = None,
    color_scheme: Literal["light", "dark", "no-preference"] | None = None,
    geoip: bool = True,
    humanize: bool = True,
    human_preset: HumanPreset = "default",
    human_config: HumanConfigOverrides | None = None,
    show_cursor: bool | None = None,
    extension_paths: list[str] | None = None,
    browser_version: str | None = None,
    persona: str | None = None,
    allow_3p_cookies: bool | None = None,
    **kwargs: Any,
) -> Any:
    """Async version of launch_context().

    Launch stealth browser and return a BrowserContext with common options pre-set.
    All extra kwargs are forwarded to ``browser.new_context()`` — use this for
    ``storage_state``, ``permissions``, ``extra_http_headers``, etc. without needing
    a persistent profile folder.

    Args:
        headless: Run in headless mode (default True).
        proxy: Proxy URL string or Playwright proxy dict (see launch() for details).
        args: Additional Chromium CLI arguments.
        extension_paths: List of Chrome extension paths to load.
        stealth_args: Include default stealth fingerprint args (default True).
        user_agent: Custom user agent string.
        viewport: Viewport size dict, e.g. {"width": 1920, "height": 1080}.
            Pass None to disable viewport emulation (use OS window size).
        locale: Browser locale, e.g. "en-US".
        timezone: IANA timezone (e.g. 'America/New_York').
        color_scheme: Color scheme preference — 'light', 'dark', or 'no-preference'.
        geoip: Map timezone, locale, and ``navigator.languages`` to the egress IP
            (proxy exit, or the machine public IP when there is no proxy). Default
            True. Pass ``geoip=False`` to opt out. Explicit ``timezone=`` /
            ``locale=`` still win. This function resolves GeoIP itself, then
            calls persistent with ``geoip=False`` to avoid a second lookup.
        humanize: Enable human-like mouse, keyboard, scroll behavior (default True).
        human_preset: Humanize preset — 'default' or 'careful' (default 'default').
        human_config: Custom humanize config mapping to override preset values.
        show_cursor: Optional blue Camoufox-style ring (debug only). Default
            ``False``. Pass ``True`` in headed demos such as
            ``humanize_click_demo.py``. Real sites: keep ``False``.
        **kwargs: Passed to browser.new_context() — e.g. storage_state, permissions.

    Returns:
        Playwright BrowserContext object (async API).
        Call ``await .close()`` when done — this also closes the underlying browser.

    Example:
        >>> import asyncio
        >>> from hexium_browser import launch_context_async
        >>>
        >>> async def main():
        ...     # Load saved session (cookies, localStorage)
        ...     ctx = await launch_context_async(
        ...         headless=True,
        ...         storage_state="state.json",
        ...     )
        ...     page = await ctx.new_page()
        ...     await page.goto("https://example.com")
        ...     # Save state back
        ...     await ctx.storage_state(path="state.json")
        ...     await ctx.close()
        >>>
        >>> asyncio.run(main())
    """
    _check_removed_kwargs(kwargs)

    timezone = _resolve_timezone(timezone, kwargs)
    timezone, locale, exit_ip = maybe_resolve_geoip(geoip, proxy, timezone, locale, args)
    args = _append_webrtc_exit_ip(args, exit_ip)
    user_data_dir = kwargs.pop("user_data_dir", None)
    profile_name = kwargs.pop("profile", None)
    ephemeral = kwargs.pop("ephemeral", False)
    profile_path = resolve_launch_user_data_dir(
        user_data_dir, profile=profile_name, ephemeral=ephemeral
    )
    return await launch_persistent_context_async(
        profile_path,
        headless=headless,
        proxy=proxy,
        args=args,
        stealth_args=stealth_args,
        fingerprint=fingerprint,
        user_agent=user_agent,
        viewport=viewport,
        locale=locale,
        timezone=timezone,
        color_scheme=color_scheme,
        geoip=False,
        humanize=humanize,
        human_preset=human_preset,
        human_config=human_config,
        show_cursor=show_cursor,
        extension_paths=extension_paths,
        browser_version=browser_version,
        persona=persona,
        allow_3p_cookies=allow_3p_cookies,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_proxy_scheme(proxy_url: str) -> str:
    """Prepend http:// to schemeless proxy URLs so parsers can extract hostname."""
    return proxy_url if "://" in proxy_url else f"http://{proxy_url}"


def _assemble_proxy_url(
    scheme: str,
    host: str,
    port: int | None,
    enc_user: str,
    enc_pass: str | None,
    path: str = "",
    params: str = "",
    query: str = "",
    fragment: str = "",
) -> str:
    """Build a proxy URL from already-percent-encoded credentials and host parts.

    ``enc_pass is None`` means no password (no colon in userinfo). Empty string
    means present-but-empty (colon preserved). This mirrors the distinction
    urlparse makes between ``user@host`` and ``user:@host``.
    """
    if ":" in host:  # IPv6 literal — re-add brackets
        host = f"[{host}]"
    if enc_pass is not None:
        userinfo = f"{enc_user}:{enc_pass}@"
    elif enc_user:
        userinfo = f"{enc_user}@"
    else:
        userinfo = ""
    netloc = f"{userinfo}{host}"
    if port is not None:
        netloc += f":{port}"
    return urlunparse((scheme, netloc, path, params, query, fragment))


def _reconstruct_socks_url(proxy: ProxySettings) -> str:
    """Reconstruct a SOCKS5 URL with inline credentials from a Playwright proxy dict."""
    server = proxy.get("server", "")
    username = proxy.get("username", "")
    password = proxy.get("password", "")
    if not username:
        return server
    parsed = urlparse(server)
    enc_user = quote(username, safe="")
    # Dict convention: empty/missing password → no colon.
    enc_pass = quote(password, safe="") if password else None
    return _assemble_proxy_url(
        parsed.scheme, parsed.hostname or "", parsed.port,
        enc_user, enc_pass, parsed.path,
    )


def _normalize_socks_string_url(url: str) -> str:
    """Re-encode credentials in a SOCKS5 URL string so Chromium's parser doesn't
    truncate them at special chars like '='. Idempotent: pre-encoded input stays
    the same (decoded then re-encoded).

    Emits an INFO log when re-encoding actually changes the URL, so users who
    previously hit silent SOCKS5 fallback (#157) can see what the wrapper did.
    Silent on already-encoded inputs (no false-positive noise).

    On unparseable input (invalid port, broken IPv6 literal, etc.) logs a
    warning and returns the original string — preserves pre-fix pass-through
    behavior so Chromium's own error handling kicks in.
    """
    try:
        parsed = urlparse(url)
        # Accessing .port raises ValueError on invalid port strings.
        _ = parsed.port
    except ValueError as e:
        logger.warning("Malformed SOCKS5 proxy URL, passing through unchanged: %s", e)
        return url
    # Skip only if no credentials at all (username AND password both absent).
    # urlparse returns None for absent components, "" for present-but-empty.
    if parsed.username is None and parsed.password is None:
        return url
    raw_user = parsed.username or ""
    enc_user = quote(unquote(raw_user), safe="") if raw_user else ""
    # Preserve the colon separator when password component is present, even if
    # empty, so `user:@host` stays `user:@host`.
    if parsed.password is not None:
        raw_pass = parsed.password
        enc_pass = quote(unquote(raw_pass), safe="") if raw_pass else ""
    else:
        raw_pass = None
        enc_pass = None
    normalized = _assemble_proxy_url(
        parsed.scheme, parsed.hostname or "", parsed.port,
        enc_user, enc_pass,
        parsed.path, parsed.params, parsed.query, parsed.fragment,
    )
    # Compare credentials, not the full URL: urlparse cosmetically lowercases
    # scheme and hostname, so a full-string compare would falsely fire on
    # `socks5://USER:pass@HOST.com:1080` even when no encoding work happened.
    if enc_user != raw_user or enc_pass != raw_pass:
        logger.info(
            "Auto URL-encoded SOCKS5 proxy credentials (special characters "
            "detected). Pre-encode the URL to suppress this notice."
        )
    return normalized


def _extract_proxy_url(proxy: str | ProxySettings | None) -> str | None:
    """Extract and normalize proxy URL string from proxy param.

    For proxy dicts with separate username/password fields, reconstructs
    the full URL with inline credentials so proxy auth works.
    """
    if proxy is None:
        return None
    if isinstance(proxy, dict):
        server = proxy.get("server", "")
        if not server:
            return None
        if proxy.get("username"):
            return (
                _reconstruct_socks_url(proxy) if _is_socks_proxy(proxy)
                else _reconstruct_http_url(proxy)
            )
        return _ensure_proxy_scheme(server)
    return _ensure_proxy_scheme(proxy)


def _get_flag_value(args: list[str] | None, *keys: str) -> str | None:
    """Return the value of the first ``--key=value`` flag found in *args*, else None."""
    for a in args or []:
        for k in keys:
            if a.startswith(k + "="):
                return a.split("=", 1)[1]
    return None


def maybe_resolve_geoip(
    geoip: bool,
    proxy: str | ProxySettings | None,
    timezone: str | None,
    locale: str | None,
    args: list[str] | None = None,
) -> tuple[str | None, str | None, str | None]:
    """Auto-fill timezone/locale from the egress IP when geoip is enabled.

    Returns ``(timezone, locale, exit_ip)``.  *exit_ip* is a free bonus
    from the geoip lookup (no extra HTTP call) — used for WebRTC spoofing.

    With a proxy the egress IP is the proxy's exit IP; with no proxy it is
    the machine's own public IP, so geoip works proxy-free too.

    A timezone/locale set as a raw flag in *args* (``--hexium-timezone``,
    ``--lang``, ``--hexium-locale``) counts as explicit: it is promoted to
    the param so geoip leaves it alone, mirroring the ``timezone=``/``locale=``
    override path.
    """
    if not geoip:
        return timezone, locale, None

    # Promote raw flags to explicit params so geoip doesn't clobber them.
    if timezone is None:
        timezone = _get_flag_value(args, "--hexium-timezone")
    if locale is None:
        locale = _get_flag_value(args, "--lang", "--hexium-locale")

    from .geoip import resolve_proxy_exit_ip, resolve_proxy_geo_with_ip

    # None when no proxy → echo services resolve the machine's own public IP
    proxy_url = _extract_proxy_url(proxy) if proxy else None

    # When both tz/locale are explicit, resolve the exit IP for WebRTC — but only
    # with a proxy. With no proxy the WebRTC IP would just be the real connection
    # IP the site already sees (a no-op), so skip the third-party echo call.
    if timezone is not None and locale is not None:
        exit_ip = resolve_proxy_exit_ip(proxy_url) if proxy_url else None
        return timezone, locale, exit_ip

    geo_tz, geo_locale, exit_ip = resolve_proxy_geo_with_ip(proxy_url)
    if timezone is None:
        timezone = geo_tz
    if locale is None:
        locale = geo_locale
    return timezone, locale, exit_ip


def _resolve_webrtc_args(
    args: list[str] | None,
    proxy: str | ProxySettings | None,
) -> list[str] | None:
    """Replace --hexium-webrtc-ip=auto with the resolved proxy exit IP.

    Returns args unchanged if no ``auto`` value is present.
    """
    if not args:
        return args
    idx = None
    for i, a in enumerate(args):
        if a == "--hexium-webrtc-ip=auto":
            idx = i
            break
    if idx is None:
        return args
    proxy_url = _extract_proxy_url(proxy)
    if not proxy_url:
        logger.warning("--hexium-webrtc-ip=auto requires a proxy; removing flag")
        args = list(args)
        del args[idx]
        return args
    try:
        from .geoip import resolve_proxy_exit_ip
        exit_ip = resolve_proxy_exit_ip(proxy_url)
    except Exception:
        logger.warning("Failed to resolve proxy exit IP for WebRTC spoofing; removing --hexium-webrtc-ip=auto")
        args = list(args)
        del args[idx]
        return args
    if exit_ip:
        args = list(args)
        args[idx] = f"--hexium-webrtc-ip={exit_ip}"
    else:
        logger.warning("Could not resolve proxy exit IP for WebRTC spoofing; removing --hexium-webrtc-ip=auto")
        args = list(args)
        del args[idx]
    return args


def _append_webrtc_exit_ip(
    args: list[str] | None, exit_ip: str | None
) -> list[str] | None:
    """Append ``--hexium-webrtc-ip=<exit_ip>`` unless the user already set it.

    *exit_ip* comes free from the geoip lookup; it spoofs the WebRTC IP to the
    egress IP. No-op when there is no exit IP or the flag is already present. This
    rule must stay identical across every launch path, so it lives in one place.
    """
    if exit_ip and not (args and any(a.startswith("--hexium-webrtc-ip") for a in args)):
        args = list(args or [])
        args.append(f"--hexium-webrtc-ip={exit_ip}")
        logger.info("WebRTC egress IP set to %s (matches GeoIP proxy exit)", exit_ip)
    return args


WEBRTC_MASK_ENV = "HEXIUM_WEBRTC_MASK_IP"


def webrtc_mask_ip_from_args(args: list[str] | None) -> str | None:
    """Return ``--hexium-webrtc-ip=`` value, ignoring ``auto``."""
    for a in args or []:
        if a.startswith("--hexium-webrtc-ip="):
            value = a.split("=", 1)[1].strip()
            if value and value != "auto":
                return value
    return None


def _ensure_webrtc_mask_env(kwargs: dict[str, Any], chrome_args: list[str] | None) -> None:
    """Publish the ICE mask IP to Chromium children (zygote/renderer).

    ``--hexium-webrtc-ip`` is not always copied onto renderer argv. The
    environment is inherited, so HEXIUM_WEBRTC_MASK_IP fills host/srflx ICE.
    """
    ip = webrtc_mask_ip_from_args(chrome_args)
    if not ip:
        return
    os.environ[WEBRTC_MASK_ENV] = ip
    existing = kwargs.get("env")
    env = dict(existing) if existing is not None else dict(os.environ)
    env[WEBRTC_MASK_ENV] = ip
    kwargs["env"] = env


def _apply_linux_windows_chrome_webgpu_flags(
    seen: dict[str, str], fingerprint: str | None
) -> None:
    """Enable Linux experimental WebGPU for windows-chrome (including headless).

    Chrome 151 leaves kWebGPUService off on Linux, so requestAdapter() is
    null unless --enable-unsafe-webgpu is set. Vulkan is Dawn's Linux
    backend; a disabled Vulkan feature also yields a null adapter.
    """
    import platform as _platform

    if _platform.system() != "Linux":
        return
    if fingerprint == "off" or seen.get("--hexium-fingerprint") == "--hexium-fingerprint=off":
        return
    raw = seen.get("--hexium-persona", "")
    if not raw.startswith("--hexium-persona="):
        return
    if normalize_persona_preset(raw.split("=", 1)[1]) != "windows-chrome":
        return
    seen.setdefault("--ignore-gpu-blocklist", "--ignore-gpu-blocklist")
    seen.setdefault("--enable-unsafe-webgpu", "--enable-unsafe-webgpu")
    key = "--enable-features"
    current = seen[key].split("=", 1)[-1] if key in seen else ""
    features = [f for f in current.split(",") if f]
    if "Vulkan" not in features:
        features.append("Vulkan")
        seen[key] = f"{key}={','.join(features)}"


def build_args(
    stealth_args: bool,
    extra_args: list[str] | None,
    timezone: str | None = None,
    locale: str | None = None,
    headless: bool = True,
    extension_paths: list[str] | None = None,
    start_maximized: bool = False,
    fingerprint: str | None = None,
    user_data_dir: str | os.PathLike | None = None,
    persona: str | None = None,
    allow_3p_cookies: bool | None = None,
) -> list[str]:
    """Combine stealth args with user-provided args and locale flags.

    Deduplicates by flag key (everything before '=').
    Priority: stealth defaults < user args < dedicated params (timezone/locale/persona).
    On Linux the default persona is ``linux-native`` (host GPU/fonts/screen).
    Windows default is ``windows-native``; macOS default is ``macos-native``.
    Pass ``linux-chrome`` to sample Linux screen/hw, or ``windows-chrome``
    (alias ``windows-1080p``) for Win32 UA + FONTCONFIG. Those write
    ``user_data_dir/persona.json`` as ``--hexium-persona-file``.
    ``fingerprint="off"`` and ``*-native`` skip the file.
    """
    seen: dict[str, str] = {}

    if (
        stealth_args
        and fingerprint is None
        and user_data_dir
        and not _is_ephemeral_profile(user_data_dir)
    ):
        stored = load_persona_json(user_data_dir)
        stored_seed = None if stored is None else stored.get("fingerprint_seed")
        if stored_seed:
            fingerprint = str(stored_seed)

    if stealth_args:
        for arg in get_default_stealth_args(fingerprint):
            seen[arg.split("=", 1)[0]] = arg

    # Lingmo GTK3 SIGSEGV on headed GUI. Independent of stealth_args so
    # stealth_args=False still launches a window. User extra_args override.
    if not headless:
        for arg in linux_headed_gui_args():
            seen[arg.split("=", 1)[0]] = arg
    else:
        for arg in linux_headless_gl_args():
            seen[arg.split("=", 1)[0]] = arg

    # GPU blocklist bypass:
    # - Headed mode (all platforms): Chromium blocks WebGL on software GPUs
    #   in Docker/Xvfb. Flag lets SwiftShader serve WebGL. See issue #56.
    # - Windows (all modes): Chromium's GPU blocklist blocks WebGPU for the
    #   Microsoft Basic Render Driver. Dawn's adapter_blocklist bypass alone
    #   isn't enough — need this flag too.
    # Headless Linux (linux-native / linux-chrome) skips this to avoid forcing
    # a software ANGLE path; Playwright SwiftShader is already ignored.
    # Linux windows-chrome (including headless) is applied after persona merge.
    import platform as _platform
    if not headless or _platform.system() == "Windows":
        seen["--ignore-gpu-blocklist"] = "--ignore-gpu-blocklist"

    if extra_args:
        for arg in extra_args:
            key = arg.split("=", 1)[0]
            if key == "--hexium-persona" and "=" in arg:
                arg = f"--hexium-persona={normalize_persona_preset(arg.split('=', 1)[1])}"
            if key in seen:
                logger.debug("Arg override: %s -> %s", seen[key], arg)
            seen[key] = arg

    if persona:
        seen["--hexium-persona"] = (
            f"--hexium-persona={normalize_persona_preset(persona)}"
        )

    if allow_3p_cookies_enabled(allow_3p_cookies):
        seen.setdefault("--hexium-allow-3p-cookies", "--hexium-allow-3p-cookies")

    _apply_linux_windows_chrome_webgpu_flags(seen, fingerprint)

    # Playwright's default launch args switch off a browser feature that stock Chrome
    # ships enabled. Re-enable it alongside the Windows font-metrics profile so the
    # feature set matches a stock browser rather than a test harness. Merged into any
    # existing --enable-features value rather than added as a second flag.
    if "--hexium-windows-font-metrics" in seen:
        key = "--enable-features"
        current = seen[key].split("=", 1)[-1] if key in seen else ""
        features = [f for f in current.split(",") if f]
        if "MediaRouter" not in features:
            features.append("MediaRouter")
            seen[key] = f"{key}={','.join(features)}"

    # Timezone/locale flags are independent of stealth_args — always inject when set
    if timezone:
        key = "--hexium-timezone"
        flag = f"{key}={timezone}"
        if key in seen:
            logger.debug("Arg override: %s -> %s", seen[key], flag)
        seen[key] = flag
    if locale:
        from .geoip import chrome_lang_for_locale
        from .persona.geo_overlay import languages_from_locale

        chrome_lang = chrome_lang_for_locale(locale) or locale
        languages = languages_from_locale(locale)
        language_list = ",".join(languages)
        lang_flags = {
            "--lang": f"--lang={chrome_lang}",
            "--hexium-locale": f"--hexium-locale={language_list}",
            "--accept-lang": f"--accept-lang={language_list}",
        }
        for key, flag in lang_flags.items():
            if key in seen:
                logger.debug("Arg override: %s -> %s", seen[key], flag)
            seen[key] = flag

    if extension_paths:
        abs_paths = [os.path.abspath(p) for p in extension_paths]
        ext_val = ",".join(abs_paths)

        seen["--load-extension"] = f"--load-extension={ext_val}"
        seen["--disable-extensions-except"] = (
            f"--disable-extensions-except={ext_val}"
        )

    # Open maximized (real Windows Chrome overwhelmingly runs maximized) so the
    # window fills the spoofed screen. Skipped if the caller already chose a
    # window geometry. Gated to binaries where this stays coherent (see
    # binary_supports_maximized_window) — below the gate it would create
    # outerWidth < innerWidth.
    if start_maximized and not any(
        k in seen for k in ("--start-maximized", "--window-size", "--window-position")
    ):
        seen["--start-maximized"] = "--start-maximized"

    _attach_persona_file(
        seen,
        fingerprint=fingerprint,
        user_data_dir=user_data_dir,
        timezone=timezone,
        locale=locale,
    )

    return list(seen.values())


def _is_ephemeral_profile(user_data_dir: str | os.PathLike) -> bool:
    return Path(os.fspath(user_data_dir)).name.startswith("hexium-session-")


def _attach_persona_file(
    seen: dict[str, str],
    fingerprint: str | None,
    user_data_dir: str | os.PathLike | None,
    timezone: str | None,
    locale: str | None,
) -> None:
    """Write persona.json into the profile and pass ``--hexium-persona-file``.

    Skipped when fingerprint spoofing is off, the caller chose linux-native (or
    another non-sampled preset), the file path is already set, or there is
    no persistent profile directory to write into. ``windows-chrome`` also
    writes ``fontconfig.conf`` and refuses to launch if the Windows font pack
    is missing.
    """
    if fingerprint == "off" or seen.get("--hexium-fingerprint") == "--hexium-fingerprint=off":
        return
    raw = seen.get("--hexium-persona")
    if not raw or not raw.startswith("--hexium-persona="):
        return
    preset = normalize_persona_preset(raw.split("=", 1)[1])
    seen["--hexium-persona"] = f"--hexium-persona={preset}"
    if preset not in {"linux-chrome", "windows-chrome"}:
        return
    if "--hexium-persona-file" in seen:
        return
    if not user_data_dir:
        return
    seed_flag = seen.get("--hexium-seed")
    if not seed_flag or "=" not in seed_flag:
        return
    seed = seed_flag.split("=", 1)[1]
    if not seed:
        return

    if preset == "windows-chrome":
        generate_windows_fontconfig(user_data_dir)

    persona = None
    if not _is_ephemeral_profile(user_data_dir):
        existing = load_persona_json(user_data_dir)
        if existing is not None and str(existing.get("fingerprint_seed") or "") == seed:
            persona = existing

    if persona is None:
        if preset == "windows-chrome":
            persona = finalize_windows_persona(sample_windows_chrome(seed))
        else:
            persona = sample_linux_chrome(seed)
    else:
        # Sticky profiles skip resampling; still keep UA/CH on this engine.
        persona = rewrite_chrome_version(persona, CHROME_UA_VERSION)
        persona["ua_ch_model"] = ""
        if preset == "windows-chrome":
            persona = finalize_windows_persona(persona)
    webrtc_ip = None
    webrtc_flag = seen.get("--hexium-webrtc-ip")
    if webrtc_flag and "=" in webrtc_flag:
        value = webrtc_flag.split("=", 1)[1]
        if value and value != "auto":
            webrtc_ip = value
    apply_geoip(persona, timezone=timezone, locale=locale, exit_ip=webrtc_ip)
    path = write_persona_json(persona, user_data_dir)
    seen["--hexium-persona-file"] = f"--hexium-persona-file={path}"


def _ensure_windows_fontconfig_env(
    kwargs: dict[str, Any],
    chrome_args: list[str],
    user_data_dir: str | os.PathLike | None,
) -> None:
    """Point FONTCONFIG_FILE at the generated jail for windows-chrome."""
    if not user_data_dir:
        return
    preset = None
    for arg in chrome_args:
        if arg.startswith("--hexium-persona="):
            preset = arg.split("=", 1)[1]
    if preset != "windows-chrome":
        return
    conf = Path(os.fspath(user_data_dir)) / "fontconfig.conf"
    if not conf.is_file():
        raise WindowsFontPackError(
            f"windows-chrome FONTCONFIG_FILE missing at {conf}. "
            "Refusing Win32 UA on host fonts."
        )
    existing = kwargs.get("env")
    env = dict(existing) if existing is not None else dict(os.environ)
    env["FONTCONFIG_FILE"] = str(conf.resolve())
    kwargs["env"] = env


def _ensure_persona_json_env(
    kwargs: dict[str, Any],
    user_data_dir: str | os.PathLike | None,
) -> None:
    """Copy persona.json into HEXIUM_PERSONA_JSON so sandboxed children see it."""
    if not user_data_dir:
        return
    path = Path(os.fspath(user_data_dir)) / "persona.json"
    if not path.is_file():
        return
    existing = kwargs.get("env")
    env = dict(existing) if existing is not None else dict(os.environ)
    env["HEXIUM_PERSONA_JSON"] = path.read_text(encoding="utf-8")
    kwargs["env"] = env


# ---------------------------------------------------------------------------
# Windows-font mismatch warning (Linux + windows-chrome only)
#
# windows-chrome spoofs Win32 on a Linux host. Fonts come from the jail /
# pack. A font-less Linux box contradicts the Windows claim. Warn once per
# environment. Does not fire for windows-native (host fonts) or linux-*.
# See docs/chrome40-fpjs-font-minimum-set-investigation.md.
# ---------------------------------------------------------------------------

# Microsoft-proprietary fonts that signal a real Windows install (absent from
# ttf-mscorefonts-installer). Keep in sync with issue #395 and
# docs/chrome40-fpjs-font-minimum-set-investigation.md.
# Windows OS fonts — ship with Windows itself, so their absence on a
# Windows-spoofing Linux host degrades results. The two monospace fonts
# (Consolas + Courier New) are part of the recommended set so the generic
# `monospace` family resolves to a Windows font. See issue #395.
_WINDOWS_FONT_TELLS = (
    "Segoe UI",
    "Segoe UI Light",
    "Calibri",
    "Marlett",
    "MS UI Gothic",
    "Franklin Gothic",
    "Consolas",
    "Courier New",
)

# MS Office supplemental fonts, installed as one atomic block by every Office
# install. Roughly half of real Windows machines have this pack and half do
# not, so its absence is a perfectly normal Windows setup, NOT a problem —
# reported as an informational signal only, never a warning.
_OFFICE_FONT_TELLS = (
    "MT Extra",
    "Century",
    "Century Gothic",
    "MS Reference Specialty",
    "Wingdings 2",
    "Wingdings 3",
    "Book Antiqua",
    "Bookshelf Symbol 7",
    "Monotype Corsiva",
    "Bookman Old Style",
)

_font_warning_checked = False


def _count_fonts_present(tells: tuple[str, ...]) -> int | None:
    """Count how many tell-tale fonts are installed, via fc-list.

    Returns the number present (0..len(tells)), or None if it can't be
    determined (fc-list missing or errored). Callers must NOT treat None as
    zero — None means "unknown", 0 means "genuinely none installed".
    """
    import subprocess
    try:
        result = subprocess.run(
            ["fc-list"], capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    listing = result.stdout.lower()
    return sum(1 for font in tells if font.lower() in listing)


def _windows_fonts_present() -> bool | None:
    """True if ALL Windows OS fonts are installed, False if any are missing,
    None if unknown. Strict: a partial set is treated as incomplete, since the
    font install is atomic and a missing font degrades the Windows persona.
    """
    n = _count_fonts_present(_WINDOWS_FONT_TELLS)
    return None if n is None else n == len(_WINDOWS_FONT_TELLS)


def _maybe_warn_windows_fonts(chrome_args: list[str]) -> None:
    """Warn once when spoofing Windows on a Linux host without the full Windows
    font set.

    Best-effort and silent on error — never raises. Gated by an in-process flag
    plus a cache-dir marker so it fires at most once per environment. Suppress
    entirely with HEXIUM_SUPPRESS_FONT_WARNING.
    """
    global _font_warning_checked
    if _font_warning_checked:
        return
    _font_warning_checked = True
    try:
        import platform
        if os.environ.get("HEXIUM_SUPPRESS_FONT_WARNING"):
            return
        if platform.system() != "Linux":
            return
        # Effective platform = the last --hexium-persona in the final argv
        # (build_args dedups, so there is at most one). None => no Windows spoof.
        effective_platform = None
        for arg in chrome_args:
            if arg.startswith("--hexium-persona="):
                effective_platform = arg.split("=", 1)[1].strip().lower()
        if effective_platform != "windows-chrome":
            return
        from .config import get_cache_dir
        marker = get_cache_dir() / ".font_warning_shown"
        if marker.exists():
            return
        present = _windows_fonts_present()
        if present is None or present:
            return  # full set present, or can't determine — don't warn
        sys.stderr.write(
            "[hexium_browser] Incomplete Windows font set — install the full "
            "set when spoofing Windows on Linux "
            "(silence: HEXIUM_SUPPRESS_FONT_WARNING=1)\n"
        )
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("")
        except OSError:
            pass
    except Exception:
        pass


def _parse_socks_proxy_url(proxy: str) -> dict[str, Any]:
    """Parse SOCKS5 URL into a Playwright proxy dict (server + username/password)."""
    normalized = proxy
    if "@" in proxy and "://" not in proxy:
        normalized = f"socks5://{proxy}"
    elif "://" not in proxy:
        normalized = f"socks5://{proxy}"

    try:
        parsed = urlparse(normalized)
        _ = parsed.port
    except ValueError as e:
        logger.warning("Malformed SOCKS5 proxy URL, using Playwright dict as-is: %s", e)
        try:
            parsed = urlparse(normalized)
        except ValueError:
            return {"server": proxy if "://" in proxy else normalized}
        if not parsed.username:
            return {"server": proxy if "://" in proxy else normalized}
        result: dict[str, Any] = {"server": proxy if "://" in proxy else normalized}
        result["username"] = unquote(parsed.username)
        if parsed.password is not None:
            result["password"] = unquote(parsed.password)
        return result

    if not parsed.username:
        return {"server": proxy if "://" in proxy else normalized}

    server = _assemble_proxy_url(
        parsed.scheme or "socks5",
        parsed.hostname or "",
        parsed.port,
        "", None,
        parsed.path, parsed.params, parsed.query, parsed.fragment,
    )

    result: dict[str, Any] = {"server": server}
    result["username"] = unquote(parsed.username)
    if parsed.password is not None:
        result["password"] = unquote(parsed.password)
    return result


def _parse_proxy_url(proxy: str) -> dict[str, Any]:
    """Parse HTTP(S) proxy URL, extracting credentials into separate Playwright fields.

    Handles: http://user:pass@host:port -> {server: "http://host:port", username: "user", password: "pass"}
    Also handles: no credentials, URL-encoded special chars, missing port,
    and bare proxy strings without a scheme (e.g. 'user:pass@host:port' -> treated as http).

    SOCKS5 URLs are NOT handled here — they take a dedicated path via
    ``_normalize_socks_string_url`` in ``_resolve_proxy_config``.
    """
    # Bare format: "user:pass@host:port" — urlparse needs a scheme to extract credentials.
    normalized = proxy
    if "@" in proxy and "://" not in proxy:
        normalized = f"http://{proxy}"

    parsed = urlparse(normalized)

    if not parsed.username:
        return {"server": proxy}  # no creds — return original unchanged

    # Rebuild server URL without credentials
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc += f":{parsed.port}"

    server = urlunparse((parsed.scheme, netloc, parsed.path, "", "", ""))

    result: dict[str, Any] = {"server": server}
    result["username"] = unquote(parsed.username)
    if parsed.password:
        result["password"] = unquote(parsed.password)

    return result


def _has_credentials(proxy: str | ProxySettings) -> bool:
    """Check if the proxy has inline or dict-level credentials."""
    if isinstance(proxy, dict):
        return bool(proxy.get("username"))
    return "@" in proxy


def _reconstruct_http_url(proxy: ProxySettings) -> str:
    """Reconstruct an HTTP(S) proxy URL with inline credentials from a Playwright proxy dict."""
    server = proxy.get("server", "")
    username = proxy.get("username", "")
    password = proxy.get("password", "")
    if not username:
        return server
    parsed = urlparse(_ensure_proxy_scheme(server))
    enc_user = quote(username, safe="")
    enc_pass = quote(password, safe="") if password else None
    return _assemble_proxy_url(
        parsed.scheme, parsed.hostname or "", parsed.port,
        enc_user, enc_pass, parsed.path,
    )


def _normalize_http_string_url(url: str) -> str:
    """Re-encode credentials in an HTTP(S) proxy URL string for --proxy-server.

    Same pattern as ``_normalize_socks_string_url`` — decode then re-encode to
    ensure Chromium's proxy URL parser handles special chars correctly.
    """
    normalized = url if "://" in url else f"http://{url}"
    try:
        parsed = urlparse(normalized)
        _ = parsed.port
    except ValueError as e:
        logger.warning("Malformed HTTP proxy URL, passing through unchanged: %s", e)
        return normalized
    if parsed.username is None and parsed.password is None:
        return normalized
    raw_user = parsed.username or ""
    enc_user = quote(unquote(raw_user), safe="") if raw_user else ""
    if parsed.password is not None:
        raw_pass = parsed.password
        enc_pass = quote(unquote(raw_pass), safe="") if raw_pass else ""
    else:
        raw_pass = None
        enc_pass = None
    result = _assemble_proxy_url(
        parsed.scheme, parsed.hostname or "", parsed.port,
        enc_user, enc_pass,
        parsed.path, parsed.params, parsed.query, parsed.fragment,
    )
    if enc_user != raw_user or enc_pass != raw_pass:
        logger.info(
            "Auto URL-encoded HTTP proxy credentials (special characters "
            "detected). Pre-encode the URL to suppress this notice."
        )
    return result


def _is_socks_proxy(proxy: str | ProxySettings | None) -> bool:
    """Check if the proxy uses SOCKS5 protocol."""
    if proxy is None:
        return False
    url = proxy.get("server", "") if isinstance(proxy, dict) else proxy
    return url.lower().startswith(("socks5://", "socks5h://"))


def _with_proxy_network_compat(extra_args: list[str] | None = None) -> list[str]:
    """HTTP CONNECT proxies often hang on HTTP/2 or QUIC (e.g. Google via Playwright).

    Also force WebRTC onto the proxied path so STUN/host ICE does not use the
    machine's default UDP route (real public IP).

    ``--hexium-proxy=1`` marks a Playwright proxy session for engine HX-P2-07
    mitigation when Chromium never sees ``--proxy-server`` (credentialed HTTP
    via Playwright dict). Harmless if the binary does not define the switch.
    """
    args = list(extra_args or [])
    flags = (
        "--hexium-proxy=1",
        "--disable-http2",
        "--disable-quic",
        "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
    )
    for flag in flags:
        key = flag.split("=", 1)[0]
        if not any(a == flag or a.startswith(f"{key}=") for a in args):
            args.append(flag)
    return args


def _resolve_proxy_config(
    proxy: str | ProxySettings | None,
    browser_version: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Resolve proxy into Playwright kwargs and Chrome args.

    Credentialed proxies use Chrome's --proxy-server with inline credentials only
    when the binary ships the matching network patch (opt-in via env). Otherwise
    Playwright's proxy dict is used. SOCKS5 without credentials still uses
    --proxy-server=socks5://host:port.

    Returns:
        (proxy_kwargs, extra_chrome_args) — one or both will be empty.
    """
    if proxy is None:
        return {}, []

    if _is_socks_proxy(proxy):
        if _has_credentials(proxy) and binary_supports_socks_proxy_inline_auth(
            browser_version
        ):
            if isinstance(proxy, dict):
                url = _reconstruct_socks_url(proxy)
                extra_args = [f"--proxy-server={url}"]
                bypass = proxy.get("bypass")
                if bypass:
                    extra_args.append(f"--proxy-bypass-list={bypass}")
                return {}, _with_proxy_network_compat(extra_args)
            return {}, _with_proxy_network_compat(
                [f"--proxy-server={_normalize_socks_string_url(proxy)}"]
            )

        if _has_credentials(proxy):
            if isinstance(proxy, dict):
                return {"proxy": dict(proxy)}, _with_proxy_network_compat([])
            return {"proxy": _parse_socks_proxy_url(proxy)}, _with_proxy_network_compat([])

        if isinstance(proxy, dict):
            extra_args = [f"--proxy-server={proxy['server']}"]
            bypass = proxy.get("bypass")
            if bypass:
                extra_args.append(f"--proxy-bypass-list={bypass}")
            return {}, _with_proxy_network_compat(extra_args)
        return {}, _with_proxy_network_compat([f"--proxy-server={proxy}"])

    # HTTP/HTTPS with credentials, only on binaries that ship inline proxy auth:
    # use Chrome's native proxy authentication path instead of Playwright's CDP
    # auth interceptor (#182). Older binaries (free macOS/linux-arm64) can't parse
    # inline credentials, so they fall through to the Playwright proxy dict below.
    if _has_credentials(proxy) and binary_supports_http_proxy_inline_auth(browser_version):
        if isinstance(proxy, dict):
            url = _reconstruct_http_url(proxy)
            extra_args = [f"--proxy-server={url}"]
            bypass = proxy.get("bypass")
            if bypass:
                extra_args.append(f"--proxy-bypass-list={bypass}")
            return {}, _with_proxy_network_compat(extra_args)
        return {}, _with_proxy_network_compat(
            [f"--proxy-server={_normalize_http_string_url(proxy)}"]
        )

    # HTTP/HTTPS without credentials: use Playwright's proxy dict
    if isinstance(proxy, dict):
        return {"proxy": proxy}, _with_proxy_network_compat([])
    return {"proxy": _parse_proxy_url(proxy)}, _with_proxy_network_compat([])
