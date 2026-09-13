"""launch() uses a disk profile and tabs, not Playwright Incognito contexts."""

from unittest.mock import MagicMock, patch

import pytest

from hexium_browser.browser import (
    _PERSISTENT_NEW_CONTEXT_ERROR,
    _bind_persistent_tabs,
    _is_startup_tab,
    launch,
    launch_persistent_context,
)
from hexium_browser.config import resolve_launch_user_data_dir


def test_startup_tab_urls():
    page = MagicMock()
    page.url = "about:blank"
    assert _is_startup_tab(page) is True
    page.url = "https://www.google.com/"
    assert _is_startup_tab(page) is False


def test_bind_reuses_blank_then_opens_tab():
    blank = MagicMock()
    blank.url = "about:blank"
    extra = MagicMock()
    context = MagicMock()
    context.pages = [blank]
    context.new_page.return_value = extra
    browser = MagicMock()

    _bind_persistent_tabs(browser, context)

    first = browser.new_page()
    second = browser.new_page()
    assert first is blank
    assert second is extra
    context.new_page.assert_called_once_with()
    assert blank._hexium_isolated_evaluate is True


def test_bind_rejects_new_context():
    context = MagicMock()
    context.pages = []
    browser = MagicMock()
    _bind_persistent_tabs(browser, context)
    with pytest.raises(TypeError, match="Incognito"):
        browser.new_context()


def test_resolve_profile_never_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    monkeypatch.delenv("HEXIUM_PROFILES_DIR", raising=False)
    path = resolve_launch_user_data_dir()
    assert path.is_dir()
    assert path.parent == tmp_path / "profiles"
    assert path.name.startswith("hexium-session-")
    assert "/tmp" not in str(path) or str(tmp_path).startswith("/tmp")


def test_resolve_pinned_env(tmp_path, monkeypatch):
    pinned = tmp_path / "named-profile"
    monkeypatch.setenv("HEXIUM_USER_DATA_DIR", str(pinned))
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    path = resolve_launch_user_data_dir()
    assert path == pinned.resolve()
    assert pinned.is_dir()


def test_launch_persistent_context_rejects_tmp(monkeypatch):
    monkeypatch.delenv("HEXIUM_HOME", raising=False)
    monkeypatch.delenv("HEXIUM_PROFILES_DIR", raising=False)
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    with pytest.raises(RuntimeError, match="tmpfs|Incognito|/tmp"):
        launch_persistent_context(
            "/tmp/hexium-test-profile", headless=True, stealth_args=False
        )


@patch("hexium_browser.browser.launch_persistent_context")
def test_launch_uses_persistent_not_chromium_launch(mock_lpc, tmp_path, monkeypatch):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    monkeypatch.delenv("HEXIUM_PROFILES_DIR", raising=False)
    context = MagicMock()
    browser = MagicMock()
    context.browser = browser
    context.pages = []
    mock_lpc.return_value = context

    result = launch(headless=True, humanize=False)
    assert result is browser
    mock_lpc.assert_called_once()
    profile = mock_lpc.call_args.args[0]
    assert str(profile).startswith(str(tmp_path / "profiles"))
    assert profile.name.startswith("hexium-session-")
    with pytest.raises(TypeError, match="Incognito"):
        result.new_context()
    assert _PERSISTENT_NEW_CONTEXT_ERROR
