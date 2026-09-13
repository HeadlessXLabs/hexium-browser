"""Basic launch tests for hexium_browser."""

from pathlib import Path

import pytest
from hexium_browser import (
    launch,
    launch_async,
    launch_context,
    launch_persistent_context,
    binary_info,
)
from hexium_browser.config import (
    get_chromium_version,
    get_default_hexium_binary_path,
    get_local_binary_override,
)


def _hexium_binary_available() -> bool:
    override = get_local_binary_override()
    if override and Path(override).exists():
        return True
    if Path(get_default_hexium_binary_path()).exists():
        return True
    return False


requires_binary = pytest.mark.skipif(
    not _hexium_binary_available(),
    reason="Hexium chrome binary not built; set HEXIUM_BINARY_PATH",
)


@pytest.mark.parametrize("env", [None, "patchright"])
def test_removed_backend_kwarg_raises(env, monkeypatch):
    """The removed `backend` parameter raises a clear TypeError before any
    launch side effects, regardless of the (also removed) HEXIUM_BACKEND
    env var. Guards the patchright removal."""
    if env is None:
        monkeypatch.delenv("HEXIUM_BACKEND", raising=False)
    else:
        monkeypatch.setenv("HEXIUM_BACKEND", env)
    with pytest.raises(TypeError, match="backend"):
        launch(backend="patchright")
    with pytest.raises(TypeError, match="backend"):
        launch_context(backend="patchright")
    with pytest.raises(TypeError, match="backend"):
        launch_persistent_context("/tmp/hexium_browser-test-profile", backend="patchright")


def test_executable_path_and_channel_kwargs_raise():
    """Callers cannot swap Hexium for stock Chrome via Playwright kwargs."""
    with pytest.raises(TypeError, match="executable_path"):
        launch(executable_path="/usr/bin/google-chrome")
    with pytest.raises(TypeError, match="channel"):
        launch(channel="chrome")
    with pytest.raises(TypeError, match="executable_path"):
        launch_context(executable_path="/usr/bin/google-chrome")
    with pytest.raises(TypeError, match="channel"):
        launch_persistent_context("/tmp/hexium_browser-test-profile", channel="chrome")


def test_binary_info(tmp_path, monkeypatch):
    """binary_info() returns expected structure."""
    monkeypatch.setenv("HEXIUM_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("HEXIUM_BINARY_PATH", raising=False)
    monkeypatch.delenv("HEXIUM_BINARY", raising=False)
    info = binary_info()
    assert "platform" in info
    assert "binary_path" in info
    assert "installed" in info
    if info.get("source") == "cache":
        assert info["version"] == get_chromium_version()


@requires_binary
def test_launch_and_close():
    """Can launch browser and close it."""
    browser = launch(headless=True, humanize=True)
    assert browser.is_connected()
    browser.close()


@requires_binary
def test_launch_new_page():
    """Can create a page and navigate."""
    browser = launch(headless=True, humanize=True)
    page = browser.new_page()
    page.goto("https://example.com")
    assert "Example Domain" in page.title()
    browser.close()


@requires_binary
def test_launch_with_extra_args():
    """Can pass extra Chrome args."""
    browser = launch(headless=True, humanize=True, args=["--disable-gpu"])
    page = browser.new_page()
    page.goto("https://example.com")
    assert page.title()
    browser.close()


@requires_binary
def test_webdriver_flag():
    """navigator.webdriver should be false (patched)."""
    browser = launch(headless=True, humanize=True)
    page = browser.new_page()
    page.goto("https://example.com")
    webdriver = page.evaluate("navigator.webdriver")
    assert webdriver is False, f"navigator.webdriver should be false, got {webdriver}"
    browser.close()


@requires_binary
def test_chrome_object_exists():
    """window.chrome should exist (Playwright leaks undefined)."""
    browser = launch(headless=True, humanize=True)
    page = browser.new_page()
    page.goto("https://example.com")
    chrome_exists = page.evaluate("typeof window.chrome")
    assert chrome_exists == "object", f"window.chrome should be 'object', got '{chrome_exists}'"
    browser.close()


@requires_binary
def test_plugins_count():
    """navigator.plugins should have entries (Playwright has 0)."""
    browser = launch(headless=True, humanize=True)
    page = browser.new_page()
    page.goto("https://example.com")
    plugins = page.evaluate("navigator.plugins.length")
    assert plugins > 0, f"Expected plugins > 0, got {plugins}"
    browser.close()


@pytest.mark.asyncio
@requires_binary
async def test_launch_async():
    """Async launch works."""
    browser = await launch_async(headless=True, humanize=True)
    assert browser.is_connected()
    page = await browser.new_page()
    await page.goto("https://example.com")
    title = await page.title()
    assert "Example Domain" in title
    await browser.close()
