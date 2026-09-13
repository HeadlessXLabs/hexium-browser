"""Unit tests for config.py — platform detection, paths, stealth args."""

import json
import os
from unittest.mock import patch

import pytest

from hexium_browser.config import (
    IGNORE_DEFAULT_ARGS,
    apply_linux_headed_gui_env,
    binary_supports_headless_no_viewport,
    get_archive_ext,
    get_archive_name,
    get_binary_path,
    get_cache_dir,
    get_chromium_version,
    get_default_hexium_binary_path,
    get_default_stealth_args,
    get_download_url,
    get_download_urls,
    get_github_download_url,
    get_hexium_out_archive_path,
    get_hexium_out_root,
    get_local_binary_override,
    get_platform_tag,
    hexium_engine_release_tag,
    hexium_out_dir_name,
    linux_headed_gui_args,
    normalize_requested_version,
    parse_hexium_engine_tag,
    seed_classic_theme_prefs,
    default_hexium_binary_candidates,
)


class TestGetBinaryPath:
    def test_linux(self):
        with patch("hexium_browser.config.platform.system", return_value="Linux"):
            path = get_binary_path("151.0.7922.174.1")
            assert str(path).endswith("hexium-v151.0.7922.174.1/chrome")

    def test_darwin(self):
        with patch("hexium_browser.config.platform.system", return_value="Darwin"):
            path = get_binary_path("151.0.7922.174.1")
            assert str(path).endswith(
                "hexium-v151.0.7922.174.1/Hexium.app/Contents/MacOS/Hexium"
            )

    def test_windows(self):
        with patch("hexium_browser.config.platform.system", return_value="Windows"):
            path = get_binary_path("151.0.7922.174.1")
            assert str(path).endswith("hexium-v151.0.7922.174.1/chrome.exe")


class TestArchive:
    def test_ext_windows(self):
        with patch("hexium_browser.config.platform.system", return_value="Windows"):
            assert get_archive_ext() == ".zip"

    def test_archive_name(self):
        tag = get_platform_tag()
        ext = get_archive_ext()
        assert get_archive_name() == f"Hexium-{get_chromium_version()}-{tag}{ext}"


class TestDownloadUrl:
    def test_headlessx_format(self):
        url = get_download_url("151.0.7922.174.1")
        assert "headlessx.dev/api/download" in url
        assert "hexium-v151.0.7922.174.1" in url
        assert url.endswith("Hexium-151.0.7922.174.1-linux-x64.tar.gz") or url.endswith(
            "Hexium-151.0.7922.174.1-linux-arm64.tar.gz"
        )

    def test_github_fallback_format(self, monkeypatch):
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("HEXIUM_FETCH_GITHUB_FIRST", raising=False)
        with patch("hexium_browser.config.platform.system", return_value="Linux"):
            with patch("hexium_browser.config.platform.machine", return_value="x86_64"):
                url = get_github_download_url("151.0.7922.174.1")
                primary = get_download_url("151.0.7922.174.1")
                urls = get_download_urls("151.0.7922.174.1")
        assert url == (
            "https://github.com/HeadlessXLabs/hexium-browser/releases/download/"
            "Hexium-151.0.7922.174.1/Hexium-151.0.7922.174.1-linux-x64.tar.gz"
        )
        assert hexium_engine_release_tag("151.0.7922.174.1") == "Hexium-151.0.7922.174.1"
        assert parse_hexium_engine_tag("Hexium-151.0.7922.174.1") == "151.0.7922.174.1"
        assert parse_hexium_engine_tag("v0.1.0") is None
        assert urls[0] == primary
        assert urls[1] == url

    def test_github_first_on_actions(self, monkeypatch):
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        with patch("hexium_browser.config.platform.system", return_value="Linux"):
            with patch("hexium_browser.config.platform.machine", return_value="x86_64"):
                urls = get_download_urls("151.0.7922.174.1")
        assert "github.com" in urls[0]
        assert "headlessx.dev" in urls[1]


class TestStealthArgs:
    def test_default_has_seed_and_persona(self):
        args = get_default_stealth_args()
        assert any(a.startswith("--hexium-seed=") for a in args)
        assert any(a.startswith("--hexium-persona=") for a in args)

    def test_fingerprint_off(self):
        args = get_default_stealth_args("off")
        assert "--hexium-fingerprint=off" in args


class TestVersionPin:
    def test_env_pin(self, monkeypatch):
        monkeypatch.setenv("HEXIUM_VERSION", "151.0.7922.174.1")
        assert normalize_requested_version() == "151.0.7922.174.1"

    def test_invalid_pin_raises(self):
        with pytest.raises(ValueError):
            normalize_requested_version("not-a-version")


class TestCacheDir:
    def test_default(self, monkeypatch):
        monkeypatch.delenv("HEXIUM_CACHE_DIR", raising=False)
        assert str(get_cache_dir()).endswith(".hexium")

    def test_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HEXIUM_CACHE_DIR", str(tmp_path))
        assert get_cache_dir() == tmp_path


def test_chromium_version_matches_engine():
    assert get_chromium_version().startswith("151.")


def test_default_binary_path_uses_platform_and_version():
    version = get_chromium_version()
    assert hexium_out_dir_name() == f"hexium-v{version}"
    canonical = default_hexium_binary_candidates()[0]
    assert str(canonical).endswith(f"/hexium-v{version}/chrome")
    assert str(get_hexium_out_root()) in str(canonical)


def test_default_binary_path_respects_hexium_out(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_OUT", str(tmp_path))
    monkeypatch.setenv("HEXIUM_VERSION", "151.0.7922.174.1")
    with patch("hexium_browser.config.platform.system", return_value="Linux"):
        with patch("hexium_browser.config.platform.machine", return_value="x86_64"):
            path = get_default_hexium_binary_path()
            archive = get_hexium_out_archive_path()
    assert path == str(tmp_path / "hexium-v151.0.7922.174.1" / "chrome")
    assert archive == tmp_path / "hexium-v151.0.7922.174.1" / "Hexium-151.0.7922.174.1-linux-x64.tar.gz"


def test_default_binary_path_falls_back_to_legacy_out(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_OUT", str(tmp_path / "Hexium"))
    monkeypatch.delenv("HEXIUM_VERSION", raising=False)
    legacy = tmp_path / "Hexium" / "chrome"
    legacy.parent.mkdir()
    legacy.write_text("x")
    legacy.chmod(0o755)
    with patch("hexium_browser.config.platform.system", return_value="Linux"):
        with patch("hexium_browser.config.platform.machine", return_value="x86_64"):
            assert get_default_hexium_binary_path() == str(legacy)


def test_default_binary_path_falls_back_to_legacy_hexium_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_OUT", str(tmp_path))
    monkeypatch.delenv("HEXIUM_VERSION", raising=False)
    legacy = tmp_path / "Hexium" / "chrome"
    legacy.parent.mkdir()
    legacy.write_text("x")
    legacy.chmod(0o755)
    with patch("hexium_browser.config.platform.system", return_value="Linux"):
        with patch("hexium_browser.config.platform.machine", return_value="x86_64"):
            assert get_default_hexium_binary_path() == str(legacy)


def test_tagged_out_path_wins_over_legacy(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_OUT", str(tmp_path))
    monkeypatch.setenv("HEXIUM_VERSION", "151.0.7922.174.1")
    tagged = tmp_path / "hexium-v151.0.7922.174.1" / "chrome"
    tagged.parent.mkdir()
    tagged.write_text("tagged")
    tagged.chmod(0o755)
    legacy = tmp_path / "Hexium" / "chrome"
    legacy.parent.mkdir()
    legacy.write_text("legacy")
    legacy.chmod(0o755)
    with patch("hexium_browser.config.platform.system", return_value="Linux"):
        with patch("hexium_browser.config.platform.machine", return_value="x86_64"):
            assert get_default_hexium_binary_path() == str(tagged)


def test_headless_no_viewport_supported_for_v151():
    assert binary_supports_headless_no_viewport("151.0.7922.174.1")


class TestLocalBinaryOverride:
    def test_path_wins_over_alias(self, monkeypatch):
        monkeypatch.setenv("HEXIUM_BINARY_PATH", "/tmp/hexium-path")
        monkeypatch.setenv("HEXIUM_BINARY", "/tmp/hexium-alias")
        assert get_local_binary_override() == "/tmp/hexium-path"

    def test_alias_when_path_unset(self, monkeypatch):
        monkeypatch.delenv("HEXIUM_BINARY_PATH", raising=False)
        monkeypatch.setenv("HEXIUM_BINARY", "/tmp/hexium-alias")
        assert get_local_binary_override() == "/tmp/hexium-alias"

    def test_empty_string_is_unset(self, monkeypatch):
        monkeypatch.setenv("HEXIUM_BINARY_PATH", "")
        monkeypatch.setenv("HEXIUM_BINARY", "  ")
        assert get_local_binary_override() is None


def test_ignore_default_args_includes_disable_extensions():
    assert "--disable-extensions" in IGNORE_DEFAULT_ARGS
    assert "--enable-automation" in IGNORE_DEFAULT_ARGS


class TestLinuxHeadedGui:
    def test_gtk4_and_x11_when_display_set(self, monkeypatch):
        monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.delenv("HEXIUM_NO_GTK4", raising=False)
        assert linux_headed_gui_args() == ["--gtk-version=4", "--ozone-platform=x11"]

    def test_no_ozone_without_display(self, monkeypatch):
        monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("HEXIUM_NO_GTK4", raising=False)
        assert linux_headed_gui_args() == ["--gtk-version=4"]

    def test_disabled_by_env(self, monkeypatch):
        monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.setenv("HEXIUM_NO_GTK4", "1")
        assert linux_headed_gui_args() == []

    def test_skipped_on_darwin(self, monkeypatch):
        monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Darwin")
        monkeypatch.setenv("DISPLAY", ":0")
        assert linux_headed_gui_args() == []

    def test_env_does_not_set_gtk_theme(self, monkeypatch):
        monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
        monkeypatch.delenv("HEXIUM_NO_GTK4", raising=False)
        monkeypatch.delenv("GTK_THEME", raising=False)
        monkeypatch.delenv("GTK_CSD", raising=False)
        env = apply_linux_headed_gui_env({})
        assert "GTK_THEME" not in env
        assert env["GTK_CSD"] == "0"

    def test_env_preserves_caller_theme(self, monkeypatch):
        monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
        monkeypatch.delenv("HEXIUM_NO_GTK4", raising=False)
        env = apply_linux_headed_gui_env({"GTK_THEME": "Custom", "DISPLAY": ":0"})
        assert env["GTK_THEME"] == "Custom"
        assert env["GTK_CSD"] == "0"


class TestClassicThemePrefs:
    def test_writes_classic_system_theme(self, tmp_path, monkeypatch):
        monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
        seed_classic_theme_prefs(tmp_path)
        prefs = json.loads((tmp_path / "Default" / "Preferences").read_text())
        assert prefs["extensions"]["theme"]["system_theme"] == 0
        assert prefs["extensions"]["theme"]["id"] == ""

    def test_overwrites_gtk_theme(self, tmp_path, monkeypatch):
        monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
        prefs_path = tmp_path / "Default" / "Preferences"
        prefs_path.parent.mkdir(parents=True)
        prefs_path.write_text(
            json.dumps({"extensions": {"theme": {"system_theme": 1, "id": "gtk"}}})
        )
        seed_classic_theme_prefs(tmp_path)
        prefs = json.loads(prefs_path.read_text())
        assert prefs["extensions"]["theme"]["system_theme"] == 0
        assert prefs["extensions"]["theme"]["id"] == ""

    def test_noop_on_darwin(self, tmp_path, monkeypatch):
        monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Darwin")
        seed_classic_theme_prefs(tmp_path)
        assert not (tmp_path / "Default" / "Preferences").exists()
