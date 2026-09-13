"""Unit tests for the Linux Windows-font mismatch warning (browser.py).

The warning fires once per environment when spoofing Windows on a font-less
Linux host. These tests mock platform, fc-list, and the cache dir so they are
host-independent and need no binary. The warning is written straight to stderr
(like the welcome banner and the JS/.NET wrappers), so capture it with capsys.
"""

import subprocess
from unittest.mock import patch

import pytest

import hexium_browser.browser as browser

WIN_ARGS = ["--hexium-persona=windows-chrome", "--no-sandbox"]
MSG = "Incomplete Windows font set"

# fc-list output containing all 8 Windows tell fonts (the complete set).
ALL_WIN_FONTS = (
    "Segoe UI:style=Regular\nSegoe UI Light:style=Light\nCalibri:style=Regular\n"
    "Marlett:style=Regular\nMS UI Gothic:style=Regular\n"
    "Franklin Gothic Medium:style=Regular\nConsolas:style=Regular\n"
    "Courier New:style=Regular"
)


@pytest.fixture(autouse=True)
def _reset_in_process_flag():
    """Each test starts with the once-per-process guard cleared."""
    browser._font_warning_checked = False
    yield
    browser._font_warning_checked = False


def _fc_list(returncode=0, stdout=""):
    """Build a subprocess.run side effect mimicking fc-list output."""
    def _run(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr="")
    return _run


def test_warns_when_no_windows_fonts(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("HEXIUM_SUPPRESS_FONT_WARNING", raising=False)
    with (
        patch("platform.system", return_value="Linux"),
        patch("subprocess.run", side_effect=_fc_list(0, "DejaVu Sans:style=Book")),
        patch("hexium_browser.config.get_cache_dir", return_value=tmp_path),
    ):
        browser._maybe_warn_windows_fonts(WIN_ARGS)
    assert MSG in capsys.readouterr().err
    assert (tmp_path / ".font_warning_shown").exists()


def test_in_process_flag_blocks_second_call(tmp_path, capsys):
    with (
        patch("platform.system", return_value="Linux"),
        patch("subprocess.run", side_effect=_fc_list(0, "DejaVu")) as mrun,
        patch("hexium_browser.config.get_cache_dir", return_value=tmp_path),
    ):
        browser._maybe_warn_windows_fonts(WIN_ARGS)
        assert MSG in capsys.readouterr().err  # first call warns (and drains buffer)
        browser._maybe_warn_windows_fonts(WIN_ARGS)
    assert MSG not in capsys.readouterr().err
    assert mrun.call_count == 1  # probe ran only once


def test_marker_suppresses_across_processes(tmp_path, capsys):
    """An existing marker (prior process) skips the warning even after a flag reset."""
    (tmp_path / ".font_warning_shown").write_text("")
    with (
        patch("platform.system", return_value="Linux"),
        patch("subprocess.run", side_effect=_fc_list(0, "DejaVu")),
        patch("hexium_browser.config.get_cache_dir", return_value=tmp_path),
    ):
        browser._maybe_warn_windows_fonts(WIN_ARGS)
    assert MSG not in capsys.readouterr().err


def test_env_suppresses_and_writes_no_marker(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("HEXIUM_SUPPRESS_FONT_WARNING", "1")
    with (
        patch("platform.system", return_value="Linux"),
        patch("subprocess.run", side_effect=_fc_list(0, "")),
        patch("hexium_browser.config.get_cache_dir", return_value=tmp_path),
    ):
        browser._maybe_warn_windows_fonts(WIN_ARGS)
    assert MSG not in capsys.readouterr().err
    assert not (tmp_path / ".font_warning_shown").exists()


def test_no_warn_on_non_linux(tmp_path, capsys):
    with (
        patch("platform.system", return_value="Darwin"),
        patch("hexium_browser.config.get_cache_dir", return_value=tmp_path),
    ):
        browser._maybe_warn_windows_fonts(WIN_ARGS)
    assert MSG not in capsys.readouterr().err


def test_no_warn_when_platform_overridden(tmp_path, capsys):
    with (
        patch("platform.system", return_value="Linux"),
        patch("hexium_browser.config.get_cache_dir", return_value=tmp_path),
    ):
        browser._maybe_warn_windows_fonts(["--hexium-persona=linux"])
    assert MSG not in capsys.readouterr().err


def test_no_warn_no_crash_when_fc_list_absent(tmp_path, capsys):
    with (
        patch("platform.system", return_value="Linux"),
        patch("subprocess.run", side_effect=FileNotFoundError()),
        patch("hexium_browser.config.get_cache_dir", return_value=tmp_path),
    ):
        browser._maybe_warn_windows_fonts(WIN_ARGS)  # must not raise
    assert MSG not in capsys.readouterr().err
    assert not (tmp_path / ".font_warning_shown").exists()


def test_no_warn_when_full_set_present(tmp_path, capsys):
    with (
        patch("platform.system", return_value="Linux"),
        patch("subprocess.run", side_effect=_fc_list(0, ALL_WIN_FONTS)),
        patch("hexium_browser.config.get_cache_dir", return_value=tmp_path),
    ):
        browser._maybe_warn_windows_fonts(WIN_ARGS)
    assert MSG not in capsys.readouterr().err


def test_warns_on_partial_set(tmp_path, capsys):
    # Only 1 of the 8 tells present — strict check treats this as incomplete.
    listing = "/usr/share/fonts/segoeui.ttf: Segoe UI:style=Regular"
    with (
        patch("platform.system", return_value="Linux"),
        patch("subprocess.run", side_effect=_fc_list(0, listing)),
        patch("hexium_browser.config.get_cache_dir", return_value=tmp_path),
    ):
        browser._maybe_warn_windows_fonts(WIN_ARGS)
    assert MSG in capsys.readouterr().err


def test_windows_native_does_not_warn(tmp_path, capsys):
    with (
        patch("platform.system", return_value="Linux"),
        patch("subprocess.run", side_effect=_fc_list(0, "DejaVu Sans:style=Book")),
        patch("hexium_browser.config.get_cache_dir", return_value=tmp_path),
    ):
        browser._maybe_warn_windows_fonts(["--hexium-persona=windows-native"])
    assert MSG not in capsys.readouterr().err
    assert not (tmp_path / ".font_warning_shown").exists()
