"""Windows font pack + FONTCONFIG_FILE jail for windows-chrome on Linux."""

from __future__ import annotations

import os
from pathlib import Path

_PACKAGED_WINDOWS_CONF = Path(__file__).resolve().parent / "data" / "windows-fonts.conf"

DEFAULT_WINDOWS_FONTS_DIR = Path.home() / ".hexium" / "fonts" / "windows"
DEFAULT_WINDOWS_FONTS_CONF = _PACKAGED_WINDOWS_CONF

_CWD_DIR_TAG = '<dir prefix="cwd">fonts</dir>'
_SEGOE_NAMES = ("segoeui.ttf", "segoeui.ttc", "seguisym.ttf")


class WindowsFontPackError(FileNotFoundError):
    """Windows-on-Linux font pack is missing; refuse Win32 UA on host Noto."""


def resolve_windows_fonts_dir(fonts_dir: str | os.PathLike | None = None) -> Path:
    """Return the Windows TTF pack, or raise if Segoe is missing.

    ``HEXIUM_FONTS_DIR`` overrides. Launch must not proceed with a Win32
    persona when this pack is absent.
    """
    if fonts_dir is not None:
        candidates = [Path(os.fspath(fonts_dir)).expanduser()]
    else:
        override = os.environ.get("HEXIUM_FONTS_DIR", "").strip()
        if override:
            candidates = [Path(override).expanduser()]
        else:
            candidates = [DEFAULT_WINDOWS_FONTS_DIR]
    last_error: WindowsFontPackError | None = None
    for raw in candidates:
        path = raw.resolve()
        if not path.is_dir():
            last_error = WindowsFontPackError(
                f"Windows font pack missing at {path}. Set HEXIUM_FONTS_DIR "
                "to a directory that contains segoeui.ttf."
            )
            continue
        if not _has_segoe(path):
            last_error = WindowsFontPackError(
                f"Windows font pack at {path} has no Segoe UI (segoeui.ttf). "
                "Refusing windows-chrome."
            )
            continue
        return path
    if last_error is not None:
        raise last_error
    raise WindowsFontPackError("Windows font pack missing. Set HEXIUM_FONTS_DIR.")


def resolve_windows_fonts_conf(template: str | os.PathLike | None = None) -> Path:
    if template is not None:
        src = Path(os.fspath(template))
        if src.is_file():
            return src
        raise WindowsFontPackError(f"Windows fonts.conf missing at {src}.")
    override = os.environ.get("HEXIUM_FONTS_CONF", "").strip()
    candidates = []
    if override:
        candidates.append(Path(override).expanduser())
    candidates.extend([DEFAULT_WINDOWS_FONTS_CONF, _PACKAGED_WINDOWS_CONF])
    for src in candidates:
        if src.is_file():
            return src
    raise WindowsFontPackError(
        "Windows fonts.conf missing. Set HEXIUM_FONTS_CONF or ship "
        f"packaged {_PACKAGED_WINDOWS_CONF}."
    )


def generate_windows_fontconfig(
    dest_dir: str | os.PathLike,
    fonts_dir: str | os.PathLike | None = None,
    template: str | os.PathLike | None = None,
) -> Path:
    """Write a FONTCONFIG_FILE whose ``<dir>`` is the absolute Windows pack path."""
    pack = resolve_windows_fonts_dir(fonts_dir)
    src = resolve_windows_fonts_conf(template)
    conf = src.read_text(encoding="utf-8")
    abs_dir = str(pack)
    if _CWD_DIR_TAG not in conf:
        raise WindowsFontPackError(
            f"{src} has no {_CWD_DIR_TAG!r}; cannot rewrite to an absolute font dir."
        )
    conf = conf.replace(_CWD_DIR_TAG, f"<dir>{abs_dir}</dir>")
    dest = Path(os.fspath(dest_dir))
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / "fontconfig.conf"
    out.write_text(conf, encoding="utf-8")
    return out


def _has_segoe(pack: Path) -> bool:
    names = {p.name.lower() for p in pack.iterdir() if p.is_file()}
    if any(name in names for name in _SEGOE_NAMES):
        return True
    return any(
        name.startswith("segoe") and name.endswith((".ttf", ".ttc", ".otf"))
        for name in names
    )
