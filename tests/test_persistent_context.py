"""Unit tests for launch_persistent_context() and launch_persistent_context_async().

All tests mock playwright to avoid needing a binary.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hexium_browser.config import DEFAULT_VIEWPORT


@pytest.fixture(autouse=True)
def _allow_tmp_profile_in_this_module(monkeypatch):
    """These unit tests mock Playwright and still pass a /tmp profile path."""
    monkeypatch.setenv("HEXIUM_ALLOW_TMP_PROFILE", "1")


def _make_mock_pw_and_context():
    """Create mock sync_playwright chain returning a mock context."""
    context = MagicMock()
    pw = MagicMock()
    pw.chromium.launch_persistent_context.return_value = context
    pw_cm = MagicMock()
    pw_cm.start.return_value = pw
    return pw_cm, pw, context


# ---------------------------------------------------------------------------
# Sync: launch_persistent_context()
# ---------------------------------------------------------------------------


@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, None, None))
def test_persistent_context_args_built(_mock_geoip, _mock_bin):
    """Stealth args + extra args combined correctly."""
    pw_cm, pw, context = _make_mock_pw_and_context()

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context
        launch_persistent_context("/tmp/profile", args=["--disable-gpu"])

    call_kwargs = pw.chromium.launch_persistent_context.call_args[1]
    assert "--disable-gpu" in call_kwargs["args"]
    # Stealth args present by default
    assert any(a.startswith("--hexium-seed=") for a in call_kwargs["args"])


@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, None, None))
def test_persistent_context_default_viewport(_mock_geoip, _mock_bin):
    """Chrome 151 headless uses no_viewport (real window size), not DEFAULT_VIEWPORT."""
    pw_cm, pw, context = _make_mock_pw_and_context()

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context
        launch_persistent_context("/tmp/profile")

    call_kwargs = pw.chromium.launch_persistent_context.call_args[1]
    assert call_kwargs.get("no_viewport") is True
    assert "viewport" not in call_kwargs


@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, None, None))
def test_persistent_context_legacy_headless_default_viewport(_mock_geoip, _mock_bin):
    """Pre-151 engines still emulate DEFAULT_VIEWPORT in headless."""
    pw_cm, pw, context = _make_mock_pw_and_context()

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context
        launch_persistent_context("/tmp/profile", browser_version="146.0.7680.177.3")

    call_kwargs = pw.chromium.launch_persistent_context.call_args[1]
    assert call_kwargs["viewport"] == DEFAULT_VIEWPORT
    assert "no_viewport" not in call_kwargs


@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, None, None))
def test_persistent_context_headed_no_viewport(_mock_geoip, _mock_bin):
    """Headed (headless=False): no_viewport=True instead of DEFAULT_VIEWPORT so the
    page tracks the real window (avoids the outerWidth < innerWidth tell)."""
    pw_cm, pw, context = _make_mock_pw_and_context()

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context
        launch_persistent_context("/tmp/profile", headless=False)

    call_kwargs = pw.chromium.launch_persistent_context.call_args[1]
    assert call_kwargs.get("no_viewport") is True
    assert "viewport" not in call_kwargs


@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, None, None))
def test_persistent_context_custom_viewport(_mock_geoip, _mock_bin):
    """Custom viewport overrides DEFAULT_VIEWPORT."""
    pw_cm, pw, context = _make_mock_pw_and_context()
    custom = {"width": 1280, "height": 720}

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context
        launch_persistent_context("/tmp/profile", viewport=custom)

    call_kwargs = pw.chromium.launch_persistent_context.call_args[1]
    assert call_kwargs["viewport"] == custom


@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, None, None))
def test_persistent_context_user_agent(_mock_geoip, _mock_bin):
    """user_agent forwarded to launch_persistent_context()."""
    pw_cm, pw, context = _make_mock_pw_and_context()

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context
        launch_persistent_context("/tmp/profile", user_agent="Custom/1.0")

    call_kwargs = pw.chromium.launch_persistent_context.call_args[1]
    assert call_kwargs["user_agent"] == "Custom/1.0"


@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
def test_persistent_context_locale_and_timezone(_mock_bin):
    """Timezone and locale flow to binary args only, NOT to CDP context kwargs."""
    pw_cm, pw, context = _make_mock_pw_and_context()

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context
        launch_persistent_context("/tmp/profile", timezone="Asia/Tokyo", locale="ja-JP")

    call_kwargs = pw.chromium.launch_persistent_context.call_args[1]
    # Binary args (native, undetectable)
    assert "--hexium-timezone=Asia/Tokyo" in call_kwargs["args"]
    assert "--lang=ja-JP" in call_kwargs["args"]
    # NOT in context kwargs (would trigger detectable CDP emulation)
    assert "timezone_id" not in call_kwargs
    assert "locale" not in call_kwargs


@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, None, None))
def test_persistent_context_color_scheme(_mock_geoip, _mock_bin):
    """color_scheme forwarded correctly."""
    pw_cm, pw, context = _make_mock_pw_and_context()

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context
        launch_persistent_context("/tmp/profile", color_scheme="dark")

    call_kwargs = pw.chromium.launch_persistent_context.call_args[1]
    assert call_kwargs["color_scheme"] == "dark"


@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=("Europe/Berlin", "de-DE", "5.6.7.8"))
@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
def test_persistent_context_geoip(_mock_bin, _mock_geoip):
    """geoip fills missing tz/locale — flows to binary args, not CDP context."""
    pw_cm, pw, context = _make_mock_pw_and_context()

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context
        launch_persistent_context("/tmp/profile", proxy="http://proxy:8080", geoip=True)

    call_kwargs = pw.chromium.launch_persistent_context.call_args[1]
    # Binary args
    assert "--hexium-timezone=Europe/Berlin" in call_kwargs["args"]
    assert "--lang=de-DE" in call_kwargs["args"]
    # NOT in context kwargs
    assert "timezone_id" not in call_kwargs
    assert "locale" not in call_kwargs


@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
def test_persistent_context_timezone_id_alias(_mock_bin):
    """timezone_id kwarg accepted as alias for timezone."""
    pw_cm, pw, context = _make_mock_pw_and_context()

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context
        launch_persistent_context("/tmp/profile", timezone_id="Europe/Paris")

    call_kwargs = pw.chromium.launch_persistent_context.call_args[1]
    assert "--hexium-timezone=Europe/Paris" in call_kwargs["args"]
    assert "timezone_id" not in call_kwargs


@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, None, None))
def test_persistent_context_close_stops_pw(_mock_geoip, _mock_bin):
    """context.close() also calls pw.stop()."""
    pw_cm, pw, context = _make_mock_pw_and_context()
    original_close = context.close

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context
        ctx = launch_persistent_context("/tmp/profile")

    ctx.close()
    original_close.assert_called_once()
    pw.stop.assert_called_once()


@patch("hexium_browser.config.get_platform_tag", return_value="darwin-arm64")
@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, None, None))
def test_persistent_context_proxy_string(_mock_geoip, _mock_bin, _mock_platform):
    """Proxy string parsed and passed (unsupported platform → Playwright dict)."""
    pw_cm, pw, context = _make_mock_pw_and_context()

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context
        launch_persistent_context(
            "/tmp/profile",
            proxy="http://user:pass@proxy:8080",
            browser_version="146.0.7680.177.3",
        )

    call_kwargs = pw.chromium.launch_persistent_context.call_args[1]
    assert call_kwargs["proxy"]["server"] == "http://proxy:8080"
    assert call_kwargs["proxy"]["username"] == "user"
    assert call_kwargs["proxy"]["password"] == "pass"


@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, None, None))
def test_persistent_context_proxy_dict(_mock_geoip, _mock_bin):
    """Proxy dict passed through."""
    pw_cm, pw, context = _make_mock_pw_and_context()
    proxy_dict = {"server": "http://proxy:8080", "bypass": ".google.com"}

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context
        launch_persistent_context("/tmp/profile", proxy=proxy_dict)

    call_kwargs = pw.chromium.launch_persistent_context.call_args[1]
    assert call_kwargs["proxy"] == proxy_dict


# ---------------------------------------------------------------------------
# Async: launch_persistent_context_async()
# ---------------------------------------------------------------------------


def _make_mock_async_pw_and_context():
    """Create mock async_playwright chain returning a mock context."""
    context = AsyncMock()
    pw = AsyncMock()
    pw.chromium.launch_persistent_context.return_value = context
    pw_cm = AsyncMock()
    pw_cm.start.return_value = pw
    return pw_cm, pw, context


@pytest.mark.asyncio
@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, None, None))
async def test_persistent_context_async_args_built(_mock_geoip, _mock_bin):
    """Async launch builds args correctly."""
    pw_cm, pw, context = _make_mock_async_pw_and_context()

    with patch("playwright.async_api.async_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context_async
        await launch_persistent_context_async("/tmp/profile", args=["--disable-gpu"])

    call_kwargs = pw.chromium.launch_persistent_context.call_args[1]
    assert "--disable-gpu" in call_kwargs["args"]
    assert any(a.startswith("--hexium-seed=") for a in call_kwargs["args"])


@pytest.mark.asyncio
@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, None, None))
async def test_persistent_context_async_close_stops_pw(_mock_geoip, _mock_bin):
    """await context.close() calls await pw.stop()."""
    pw_cm, pw, context = _make_mock_async_pw_and_context()
    original_close = context.close

    with patch("playwright.async_api.async_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context_async
        ctx = await launch_persistent_context_async("/tmp/profile")

    await ctx.close()
    original_close.assert_called_once()
    pw.stop.assert_called_once()


@pytest.mark.asyncio
@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
async def test_persistent_context_async_timezone_id_alias(_mock_bin):
    """timezone_id kwarg accepted as alias in async path."""
    pw_cm, pw, context = _make_mock_async_pw_and_context()

    with patch("playwright.async_api.async_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context_async
        await launch_persistent_context_async("/tmp/profile", timezone_id="Europe/Paris")

    call_kwargs = pw.chromium.launch_persistent_context.call_args[1]
    assert "--hexium-timezone=Europe/Paris" in call_kwargs["args"]
    assert "timezone_id" not in call_kwargs


@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, None, None))
@patch("hexium_browser.browser.seed_widevine_hint")
def test_persistent_context_seeds_widevine(_mock_seed, _mock_geoip, _mock_bin):
    """Sync persistent launch seeds the Widevine hint with the profile path."""
    pw_cm, pw, context = _make_mock_pw_and_context()

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context
        launch_persistent_context("/tmp/profile")

    assert Path(_mock_seed.call_args[0][0]).resolve() == Path("/tmp/profile").resolve()
    assert _mock_seed.call_args[0][1] == "/fake/chrome"


@pytest.mark.asyncio
@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, None, None))
@patch("hexium_browser.browser.seed_widevine_hint")
async def test_persistent_context_async_seeds_widevine(_mock_seed, _mock_geoip, _mock_bin):
    """Async persistent launch seeds the Widevine hint with the profile path."""
    pw_cm, pw, context = _make_mock_async_pw_and_context()

    with patch("playwright.async_api.async_playwright", return_value=pw_cm):
        from hexium_browser.browser import launch_persistent_context_async
        await launch_persistent_context_async("/tmp/profile")

    assert Path(_mock_seed.call_args[0][0]).resolve() == Path("/tmp/profile").resolve()
    assert _mock_seed.call_args[0][1] == "/fake/chrome"
