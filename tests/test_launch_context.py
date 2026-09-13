"""Unit tests for launch_context() — persistent profile, not Playwright Incognito."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hexium_browser.browser import _VIEWPORT_UNSET, _default_no_viewport, _default_no_viewport_async
from hexium_browser.config import DEFAULT_VIEWPORT


def test_default_no_viewport_helper():
    """_default_no_viewport defaults new_page()/new_context() to no_viewport=True,
    but never overrides an explicit viewport (Playwright rejects passing both)."""
    browser = MagicMock()
    orig_new_page = browser.new_page
    orig_new_context = browser.new_context
    _default_no_viewport(browser)

    browser.new_page()
    orig_new_page.assert_called_once_with(no_viewport=True)
    browser.new_context()
    orig_new_context.assert_called_once_with(no_viewport=True)

    orig_new_page.reset_mock()
    browser.new_page(viewport={"width": 800, "height": 600})
    orig_new_page.assert_called_once_with(viewport={"width": 800, "height": 600})


@pytest.mark.asyncio
async def test_default_no_viewport_helper_async():
    browser = MagicMock()
    browser.new_page = AsyncMock()
    browser.new_context = AsyncMock()
    orig_new_page = browser.new_page
    orig_new_context = browser.new_context
    _default_no_viewport_async(browser)

    await browser.new_page()
    orig_new_page.assert_awaited_once_with(no_viewport=True)
    await browser.new_context()
    orig_new_context.assert_awaited_once_with(no_viewport=True)

    orig_new_page.reset_mock()
    await browser.new_page(viewport={"width": 800, "height": 600})
    orig_new_page.assert_awaited_once_with(viewport={"width": 800, "height": 600})


@patch("hexium_browser.browser.launch_persistent_context")
def test_launch_context_uses_persistent(mock_lpc, tmp_path, monkeypatch):
    monkeypatch.setenv("HEXIUM_PROFILES_DIR", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    context = MagicMock()
    mock_lpc.return_value = context

    from hexium_browser.browser import launch_context

    result = launch_context()
    assert result is context
    mock_lpc.assert_called_once()
    profile = mock_lpc.call_args.args[0]
    assert str(profile).startswith(str(tmp_path))
    kwargs = mock_lpc.call_args.kwargs
    assert kwargs["viewport"] is _VIEWPORT_UNSET
    assert kwargs["geoip"] is False


@patch("hexium_browser.browser.launch_persistent_context")
def test_headed_no_viewport_forwarded(mock_lpc, tmp_path, monkeypatch):
    monkeypatch.setenv("HEXIUM_PROFILES_DIR", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    mock_lpc.return_value = MagicMock()

    from hexium_browser.browser import launch_context

    launch_context(headless=False)
    assert mock_lpc.call_args.kwargs["headless"] is False
    assert mock_lpc.call_args.kwargs["viewport"] is _VIEWPORT_UNSET


@patch("hexium_browser.browser.launch_persistent_context")
def test_custom_viewport_forwarded(mock_lpc, tmp_path, monkeypatch):
    monkeypatch.setenv("HEXIUM_PROFILES_DIR", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    mock_lpc.return_value = MagicMock()
    custom = {"width": 1280, "height": 720}

    from hexium_browser.browser import launch_context

    launch_context(viewport=custom)
    assert mock_lpc.call_args.kwargs["viewport"] == custom


@patch("hexium_browser.browser.launch_persistent_context")
def test_user_agent_and_color_scheme(mock_lpc, tmp_path, monkeypatch):
    monkeypatch.setenv("HEXIUM_PROFILES_DIR", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    mock_lpc.return_value = MagicMock()

    from hexium_browser.browser import launch_context

    launch_context(user_agent="Mozilla/5.0 Custom", color_scheme="dark")
    kwargs = mock_lpc.call_args.kwargs
    assert kwargs["user_agent"] == "Mozilla/5.0 Custom"
    assert kwargs["color_scheme"] == "dark"


@patch("hexium_browser.browser.launch_persistent_context")
def test_locale_timezone_binary_not_cdp_kwargs(mock_lpc, tmp_path, monkeypatch):
    monkeypatch.setenv("HEXIUM_PROFILES_DIR", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    mock_lpc.return_value = MagicMock()

    from hexium_browser.browser import launch_context

    launch_context(locale="de-DE", timezone="America/New_York")
    kwargs = mock_lpc.call_args.kwargs
    assert kwargs["locale"] == "de-DE"
    assert kwargs["timezone"] == "America/New_York"
    assert "timezone_id" not in kwargs


@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, None, None))
@patch("hexium_browser.browser.launch_persistent_context")
def test_launch_context_omitted_geoip_resolves_then_inner_false(
    mock_lpc, mock_geoip, tmp_path, monkeypatch
):
    """Default geoip=True looks up once; inner persistent call skips a second lookup."""
    monkeypatch.setenv("HEXIUM_PROFILES_DIR", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    mock_lpc.return_value = MagicMock()

    from hexium_browser.browser import launch_context

    launch_context()
    mock_geoip.assert_called()
    assert mock_geoip.call_args.args[0] is True
    assert mock_lpc.call_args.kwargs["geoip"] is False


@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=("Europe/Berlin", "de-DE", "5.6.7.8"))
@patch("hexium_browser.browser.launch_persistent_context")
def test_geoip_resolution(mock_lpc, _mock_geoip, tmp_path, monkeypatch):
    monkeypatch.setenv("HEXIUM_PROFILES_DIR", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    mock_lpc.return_value = MagicMock()

    from hexium_browser.browser import launch_context

    launch_context(proxy="http://proxy:8080", geoip=True)
    kwargs = mock_lpc.call_args.kwargs
    assert kwargs["locale"] == "de-DE"
    assert kwargs["timezone"] == "Europe/Berlin"
    assert kwargs["geoip"] is False


@patch("hexium_browser.browser.launch_persistent_context")
def test_timezone_id_alias(mock_lpc, tmp_path, monkeypatch):
    monkeypatch.setenv("HEXIUM_PROFILES_DIR", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    mock_lpc.return_value = MagicMock()

    from hexium_browser.browser import launch_context

    launch_context(timezone_id="Europe/Paris")
    assert mock_lpc.call_args.kwargs["timezone"] == "Europe/Paris"
    assert "timezone_id" not in mock_lpc.call_args.kwargs


@patch("hexium_browser.browser.launch_persistent_context")
def test_storage_and_video_kwargs(mock_lpc, tmp_path, monkeypatch):
    monkeypatch.setenv("HEXIUM_PROFILES_DIR", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    mock_lpc.return_value = MagicMock()

    from hexium_browser.browser import launch_context

    launch_context(record_video_dir="/tmp/videos", storage_state="state.json")
    kwargs = mock_lpc.call_args.kwargs
    assert kwargs["record_video_dir"] == "/tmp/videos"
    assert kwargs["storage_state"] == "state.json"


@pytest.mark.asyncio
@patch("hexium_browser.browser.launch_persistent_context_async")
async def test_async_uses_persistent(mock_lpc, tmp_path, monkeypatch):
    monkeypatch.setenv("HEXIUM_PROFILES_DIR", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    context = AsyncMock()
    mock_lpc.return_value = context

    from hexium_browser.browser import launch_context_async

    result = await launch_context_async(storage_state="state.json")
    assert result is context
    assert mock_lpc.call_args.kwargs["storage_state"] == "state.json"
    assert mock_lpc.call_args.kwargs["viewport"] is _VIEWPORT_UNSET


def test_default_viewport_constant_unchanged():
    assert DEFAULT_VIEWPORT["width"] == 1920
