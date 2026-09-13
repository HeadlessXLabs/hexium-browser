"""Windows font pack jail: FONTCONFIG_FILE with an absolute <dir>."""

from __future__ import annotations

from pathlib import Path

import pytest

from hexium_browser.persona.fonts import (
    DEFAULT_WINDOWS_FONTS_DIR,
    WindowsFontPackError,
    generate_windows_fontconfig,
    resolve_windows_fonts_dir,
)


def _fake_pack(tmp_path: Path) -> Path:
    pack = tmp_path / "windows-fonts"
    pack.mkdir()
    (pack / "segoeui.ttf").write_bytes(b"fake")
    return pack


def test_resolve_uses_hexium_fonts_dir_override(tmp_path, monkeypatch):
    pack = _fake_pack(tmp_path)
    monkeypatch.setenv("HEXIUM_FONTS_DIR", str(pack))
    assert resolve_windows_fonts_dir() == pack.resolve()


def test_resolve_refuses_missing_pack(tmp_path, monkeypatch):
    missing = tmp_path / "no-such-fonts"
    monkeypatch.setenv("HEXIUM_FONTS_DIR", str(missing))
    with pytest.raises(WindowsFontPackError, match="HEXIUM_FONTS_DIR|font pack"):
        resolve_windows_fonts_dir()


def test_resolve_refuses_pack_without_segoe(tmp_path, monkeypatch):
    pack = tmp_path / "empty-pack"
    pack.mkdir()
    (pack / "arial.ttf").write_bytes(b"fake")
    monkeypatch.setenv("HEXIUM_FONTS_DIR", str(pack))
    with pytest.raises(WindowsFontPackError, match="Segoe|segoe"):
        resolve_windows_fonts_dir()


def test_generate_fontconfig_rewrites_dir_to_absolute(tmp_path, monkeypatch):
    pack = _fake_pack(tmp_path)
    monkeypatch.setenv("HEXIUM_FONTS_DIR", str(pack))
    dest = tmp_path / "profile"
    dest.mkdir()
    conf_path = generate_windows_fontconfig(dest)
    text = conf_path.read_text(encoding="utf-8")
    abs_dir = str(pack.resolve())
    assert f"<dir>{abs_dir}</dir>" in text
    assert 'prefix="cwd"' not in text
    assert abs_dir.startswith("/")
    assert conf_path.is_file()


def test_default_fonts_dir_points_at_engine_windows_pack():
    assert DEFAULT_WINDOWS_FONTS_DIR == Path(
        "/Drive512/hexium/engine/bundle/fonts/windows"
    )
