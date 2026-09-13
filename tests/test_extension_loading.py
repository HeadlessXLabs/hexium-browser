import os
from unittest.mock import MagicMock, patch

from hexium_browser import launch


@patch("hexium_browser.browser.ensure_binary")
@patch("playwright.sync_api.sync_playwright")
def test_extension_loading(mock_sync_playwright, mock_ensure_binary, tmp_path, monkeypatch):
    monkeypatch.setenv("HEXIUM_PROFILES_DIR", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    mock_ensure_binary.return_value = "/fake/chrome"

    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_context.browser = mock_browser
    mock_context.pages = []

    mock_pw = MagicMock()
    mock_pw.chromium.launch_persistent_context.return_value = mock_context
    mock_sync_playwright.return_value.start.return_value = mock_pw

    launch(extension_paths=["./ext"])

    mock_pw.chromium.launch.assert_not_called()
    mock_pw.chromium.launch_persistent_context.assert_called_once()

    launch_call = mock_pw.chromium.launch_persistent_context.call_args
    args = launch_call.kwargs["args"]
    abs_path = os.path.abspath("./ext")

    assert f"--load-extension={abs_path}" in args
    assert f"--disable-extensions-except={abs_path}" in args
    assert "--disable-extensions" in launch_call.kwargs["ignore_default_args"]
