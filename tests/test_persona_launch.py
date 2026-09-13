"""launch()/build_args linux-chrome persona file wiring."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.persona_fixtures import linux_chrome_149_fingerprint, windows_chrome_147_fingerprint

from hexium_browser.browser import build_args, _ensure_windows_fontconfig_env, _ensure_persona_json_env
from hexium_browser.config import get_default_stealth_args
from hexium_browser.persona.fonts import WindowsFontPackError
from hexium_browser.persona.schema import CHROME_UA_VERSION


def _sample_stub(_seed: str):
    from hexium_browser.persona.coerce import coerce_fingerprint
    from hexium_browser.persona.rewrite_ua import rewrite_chrome_version

    return rewrite_chrome_version(
        coerce_fingerprint(linux_chrome_149_fingerprint(), seed=_seed),
        CHROME_UA_VERSION,
    )


def _windows_sample_stub(_seed: str):
    from hexium_browser.persona.coerce import coerce_fingerprint
    from hexium_browser.persona.rewrite_ua import rewrite_chrome_version

    return rewrite_chrome_version(
        coerce_fingerprint(windows_chrome_147_fingerprint(), seed=_seed),
        CHROME_UA_VERSION,
    )


def _install_font_pack(tmp_path: Path, monkeypatch) -> Path:
    pack = tmp_path / "win-fonts"
    pack.mkdir()
    (pack / "segoeui.ttf").write_bytes(b"fake")
    monkeypatch.setenv("HEXIUM_FONTS_DIR", str(pack))
    return pack


def test_default_linux_persona_is_linux_native(monkeypatch):
    monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
    monkeypatch.delenv("HEXIUM_PERSONA", raising=False)
    args = get_default_stealth_args("seed-1")
    assert "--hexium-persona=linux-native" in args
    assert "--hexium-seed=seed-1" in args


def test_hexium_persona_env_selects_linux_chrome(monkeypatch):
    monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
    monkeypatch.setenv("HEXIUM_PERSONA", "linux-chrome")
    args = get_default_stealth_args("seed-1")
    assert "--hexium-persona=linux-chrome" in args


def test_build_args_writes_persona_file(tmp_path):
    with patch("hexium_browser.browser.sample_linux_chrome", side_effect=_sample_stub):
        args = build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint="seed-1",
            user_data_dir=tmp_path,
            persona="linux-chrome",
        )
    file_args = [a for a in args if a.startswith("--hexium-persona-file=")]
    assert len(file_args) == 1
    path = file_args[0].split("=", 1)[1]
    assert path == str(tmp_path / "persona.json")
    data = json.loads((tmp_path / "persona.json").read_text())
    assert data["platform"] == "Linux x86_64"
    assert data["fingerprint_seed"] == "seed-1"
    assert data["use_native_surfaces"] is True
    assert "webgl_renderer" not in data
    assert "font_families" not in data
    assert "--hexium-persona=linux-chrome" in args
    assert "--hexium-seed=seed-1" in args


def test_build_args_prefers_explicit_timezone(tmp_path):
    with patch("hexium_browser.browser.sample_linux_chrome", side_effect=_sample_stub):
        args = build_args(
            stealth_args=True,
            extra_args=["--hexium-timezone=Europe/London"],
            timezone="America/New_York",
            fingerprint="seed-1",
            user_data_dir=tmp_path,
            persona="linux-chrome",
        )
    tz_args = [a for a in args if a.startswith("--hexium-timezone=")]
    assert tz_args == ["--hexium-timezone=America/New_York"]
    data = json.loads((tmp_path / "persona.json").read_text())
    assert data["timezone_id"] == "America/New_York"


def test_linux_native_extra_args_skips_persona_file(tmp_path):
    with patch("hexium_browser.browser.sample_linux_chrome", side_effect=_sample_stub) as sample:
        args = build_args(
            stealth_args=True,
            extra_args=["--hexium-persona=linux-native"],
            fingerprint="seed-1",
            user_data_dir=tmp_path,
        )
    sample.assert_not_called()
    assert not any(a.startswith("--hexium-persona-file=") for a in args)
    assert "--hexium-persona=linux-native" in args
    assert not (tmp_path / "persona.json").exists()


def test_fingerprint_off_skips_persona_file(tmp_path):
    with patch("hexium_browser.browser.sample_linux_chrome", side_effect=_sample_stub) as sample:
        args = build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint="off",
            user_data_dir=tmp_path,
        )
    sample.assert_not_called()
    assert "--hexium-fingerprint=off" in args
    assert not any(a.startswith("--hexium-persona-file=") for a in args)
    assert not any(a.startswith("--hexium-persona=") for a in args)
    assert not (tmp_path / "persona.json").exists()


def test_same_fingerprint_seed_writes_same_hardware(tmp_path):
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    with patch("hexium_browser.browser.sample_linux_chrome", side_effect=_sample_stub):
        build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint="same-seed",
            user_data_dir=dir_a,
            persona="linux-chrome",
        )
        build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint="same-seed",
            user_data_dir=dir_b,
            persona="linux-chrome",
        )
    a = json.loads((dir_a / "persona.json").read_text())
    b = json.loads((dir_b / "persona.json").read_text())
    assert a["hardware_concurrency"] == b["hardware_concurrency"]
    assert a["screen_width"] == b["screen_width"]
    assert a["device_memory_gb"] == b["device_memory_gb"]
    assert a["seed"] == b["seed"]


def test_windows_chrome_extra_args_writes_gpu_fonts(tmp_path, monkeypatch):
    pack = _install_font_pack(tmp_path, monkeypatch)
    profile = tmp_path / "profile"
    profile.mkdir()
    with patch("hexium_browser.browser.sample_windows_chrome", side_effect=_windows_sample_stub):
        args = build_args(
            stealth_args=True,
            extra_args=["--hexium-persona=windows-chrome"],
            fingerprint="seed-1",
            user_data_dir=profile,
        )
    assert "--hexium-persona=windows-chrome" in args
    assert "--hexium-persona=linux-chrome" not in args
    data = json.loads((profile / "persona.json").read_text())
    assert data["platform"] == "Win32"
    assert data["use_native_surfaces"] is False
    assert "D3D11" in data["webgl_renderer"]
    assert data["system_ui_font"] == "Segoe UI"
    assert "segoe ui" in data["font_families"]
    conf = (profile / "fontconfig.conf").read_text()
    assert f"<dir>{pack.resolve()}</dir>" in conf
    assert 'prefix="cwd"' not in conf


def test_windows_1080p_aliases_windows_chrome(tmp_path, monkeypatch):
    _install_font_pack(tmp_path, monkeypatch)
    profile = tmp_path / "profile"
    profile.mkdir()
    with patch("hexium_browser.browser.sample_windows_chrome", side_effect=_windows_sample_stub) as sample:
        args = build_args(
            stealth_args=True,
            extra_args=["--hexium-persona=windows-1080p"],
            fingerprint="seed-1",
            user_data_dir=profile,
        )
    sample.assert_called_once()
    assert "--hexium-persona=windows-chrome" in args
    assert "--hexium-persona=windows-1080p" not in args


def test_persona_kwarg_selects_windows_chrome(tmp_path, monkeypatch):
    _install_font_pack(tmp_path, monkeypatch)
    profile = tmp_path / "profile"
    profile.mkdir()
    with patch("hexium_browser.browser.sample_windows_chrome", side_effect=_windows_sample_stub):
        args = build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint="seed-1",
            user_data_dir=profile,
            persona="windows-chrome",
        )
    assert "--hexium-persona=windows-chrome" in args
    data = json.loads((profile / "persona.json").read_text())
    assert data["platform"] == "Win32"


def test_windows_chrome_refuses_missing_font_pack(tmp_path, monkeypatch):
    monkeypatch.setenv("HEXIUM_FONTS_DIR", str(tmp_path / "missing"))
    with patch("hexium_browser.browser.sample_windows_chrome", side_effect=_windows_sample_stub) as sample:
        with pytest.raises(WindowsFontPackError, match="font pack"):
            build_args(
                stealth_args=True,
                extra_args=["--hexium-persona=windows-chrome"],
                fingerprint="seed-1",
                user_data_dir=tmp_path,
            )
    sample.assert_not_called()
    assert not (tmp_path / "persona.json").exists()


def test_linux_chrome_does_not_write_windows_fontconfig(tmp_path):
    with patch("hexium_browser.browser.sample_linux_chrome", side_effect=_sample_stub):
        args = build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint="seed-1",
            user_data_dir=tmp_path,
            persona="linux-chrome",
        )
    assert "--hexium-persona=linux-chrome" in args
    assert not (tmp_path / "fontconfig.conf").exists()


def test_windows_chrome_prefers_explicit_timezone(tmp_path, monkeypatch):
    _install_font_pack(tmp_path, monkeypatch)
    profile = tmp_path / "profile"
    profile.mkdir()
    with patch("hexium_browser.browser.sample_windows_chrome", side_effect=_windows_sample_stub):
        args = build_args(
            stealth_args=True,
            extra_args=["--hexium-persona=windows-chrome"],
            timezone="America/Chicago",
            fingerprint="seed-1",
            user_data_dir=profile,
        )
    tz_args = [a for a in args if a.startswith("--hexium-timezone=")]
    assert tz_args == ["--hexium-timezone=America/Chicago"]
    data = json.loads((profile / "persona.json").read_text())
    assert data["timezone_id"] == "America/Chicago"
    assert data["platform"] == "Win32"


def test_windows_fontconfig_env_sets_absolute_file(tmp_path, monkeypatch):
    _install_font_pack(tmp_path, monkeypatch)
    profile = tmp_path / "profile"
    profile.mkdir()
    with patch("hexium_browser.browser.sample_windows_chrome", side_effect=_windows_sample_stub):
        args = build_args(
            stealth_args=True,
            extra_args=["--hexium-persona=windows-chrome"],
            fingerprint="seed-1",
            user_data_dir=profile,
        )
    kwargs: dict = {}
    _ensure_windows_fontconfig_env(kwargs, args, profile)
    assert kwargs["env"]["FONTCONFIG_FILE"] == str((profile / "fontconfig.conf").resolve())
    _ensure_persona_json_env(kwargs, profile)
    assert "HP EliteBook" in kwargs["env"]["HEXIUM_PERSONA_JSON"] or "Win32" in kwargs["env"]["HEXIUM_PERSONA_JSON"]


def test_linux_fontconfig_env_stays_unset(tmp_path):
    with patch("hexium_browser.browser.sample_linux_chrome", side_effect=_sample_stub):
        args = build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint="seed-1",
            user_data_dir=tmp_path,
            persona="linux-chrome",
        )
    kwargs: dict = {}
    _ensure_windows_fontconfig_env(kwargs, args, tmp_path)
    assert "env" not in kwargs


def test_default_linux_build_args_is_linux_native(tmp_path, monkeypatch):
    monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
    monkeypatch.delenv("HEXIUM_PERSONA", raising=False)
    profile = tmp_path / "named"
    profile.mkdir()
    args = build_args(
        stealth_args=True,
        extra_args=None,
        fingerprint="seed-1",
        user_data_dir=profile,
    )
    assert "--hexium-persona=linux-native" in args
    assert not (profile / "persona.json").exists()
    assert not (profile / "fontconfig.conf").exists()


def test_darwin_build_args_defaults_macos_native(tmp_path, monkeypatch):
    monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Darwin")
    monkeypatch.delenv("HEXIUM_PERSONA", raising=False)
    args = build_args(
        stealth_args=True,
        extra_args=None,
        fingerprint="seed-1",
        user_data_dir=tmp_path,
    )
    assert "--hexium-persona=macos-native" in args
    assert not (tmp_path / "persona.json").exists()
    assert not (tmp_path / "fontconfig.conf").exists()


def test_windows_build_args_defaults_windows_native(tmp_path, monkeypatch):
    monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Windows")
    monkeypatch.delenv("HEXIUM_PERSONA", raising=False)
    args = build_args(
        stealth_args=True,
        extra_args=None,
        fingerprint="seed-1",
        user_data_dir=tmp_path,
    )
    assert "--hexium-persona=windows-native" in args
    assert not (tmp_path / "persona.json").exists()
    assert not (tmp_path / "fontconfig.conf").exists()


@pytest.mark.parametrize("name", ["windows-native", "macos-native", "mac-native"])
def test_linux_wrong_os_native_remaps_and_skips_persona_file(tmp_path, monkeypatch, name):
    monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
    monkeypatch.delenv("HEXIUM_PERSONA", raising=False)
    with patch("hexium_browser.browser.sample_windows_chrome") as sample:
        args = build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint="seed-1",
            user_data_dir=tmp_path,
            persona=name,
        )
    sample.assert_not_called()
    assert "--hexium-persona=linux-native" in args
    assert f"--hexium-persona={name}" not in args
    assert not any(a.startswith("--hexium-persona-file=") for a in args)
    assert not (tmp_path / "persona.json").exists()
    assert not (tmp_path / "fontconfig.conf").exists()


def test_build_args_reuses_persona_json_without_resampling(tmp_path):
    with patch("hexium_browser.browser.sample_linux_chrome", side_effect=_sample_stub) as sample:
        first = build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint="seed-1",
            user_data_dir=tmp_path,
            persona="linux-chrome",
        )
        second = build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint="seed-1",
            user_data_dir=tmp_path,
            persona="linux-chrome",
        )
    assert sample.call_count == 1
    file_args = [a for a in second if a.startswith("--hexium-persona-file=")]
    assert file_args[0].split("=", 1)[1] == str(tmp_path / "persona.json")
    assert json.loads((tmp_path / "persona.json").read_text())["fingerprint_seed"] == "seed-1"
    assert first


def test_build_args_resamples_when_fingerprint_changes(tmp_path):
    with patch("hexium_browser.browser.sample_linux_chrome", side_effect=_sample_stub) as sample:
        build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint="seed-1",
            user_data_dir=tmp_path,
            persona="linux-chrome",
        )
        build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint="seed-2",
            user_data_dir=tmp_path,
            persona="linux-chrome",
        )
    assert sample.call_count == 2


def test_omitted_fingerprint_reuses_stored_seed(tmp_path):
    with patch("hexium_browser.browser.sample_linux_chrome", side_effect=_sample_stub) as sample:
        build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint="account-1",
            user_data_dir=tmp_path,
            persona="linux-chrome",
        )
        args = build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint=None,
            user_data_dir=tmp_path,
            persona="linux-chrome",
        )
    assert sample.call_count == 1
    assert "--hexium-seed=account-1" in args


def test_ephemeral_session_always_resamples(tmp_path):
    session = tmp_path / "hexium-session-abc"
    session.mkdir()
    with patch("hexium_browser.browser.sample_linux_chrome", side_effect=_sample_stub) as sample:
        build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint="seed-1",
            user_data_dir=session,
            persona="linux-chrome",
        )
        build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint="seed-1",
            user_data_dir=session,
            persona="linux-chrome",
        )
    assert sample.call_count == 2


def test_windows_named_profile_reuses_persona(tmp_path, monkeypatch):
    _install_font_pack(tmp_path, monkeypatch)
    profile = tmp_path / "Work"
    profile.mkdir()
    with patch("hexium_browser.browser.sample_windows_chrome", side_effect=_windows_sample_stub) as sample:
        build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint="account-1",
            user_data_dir=profile,
            persona="windows-chrome",
        )
        args = build_args(
            stealth_args=True,
            extra_args=None,
            fingerprint=None,
            user_data_dir=profile,
            persona="windows-chrome",
        )
    assert sample.call_count == 1
    assert "--hexium-persona=windows-chrome" in args
    assert "--hexium-seed=account-1" in args
    assert (profile / "fontconfig.conf").is_file()
