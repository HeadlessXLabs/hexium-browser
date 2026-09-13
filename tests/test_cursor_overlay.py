"""Unit tests for the virtual mouse pointer (no browser binary required)."""

from hexium_browser.human.config import resolve_config
from hexium_browser.human.cursor_overlay import get_cursor_init_script


def test_show_cursor_flag_off_by_default():
    cfg = resolve_config("default")
    assert cfg.show_cursor_overlay is False


def test_show_cursor_follows_humanize():
    from hexium_browser.browser import _resolve_human_config, _resolve_show_cursor

    assert _resolve_show_cursor(None, True) is True
    assert _resolve_show_cursor(None, False) is False
    assert _resolve_show_cursor(False, True) is False
    assert _resolve_show_cursor(True, False) is True
    assert _resolve_human_config("default", None, True).show_cursor_overlay is True
    assert _resolve_human_config("default", None, False).show_cursor_overlay is False
    assert (
        _resolve_human_config("default", {"show_cursor_overlay": True}, False).show_cursor_overlay
        is False
    )


def test_init_script_is_mouse_pointer_not_blue_ring():
    cfg = resolve_config("default", {"show_cursor_overlay": True})
    script = get_cursor_init_script(cfg)
    assert "hexium-cursor-highlighter" not in script
    assert "59, 130, 246" not in script
    assert "cursor: none" in script
    assert "<svg" in script
    assert 'fill="#fff"' in script
    assert "addEventListener(\"mousemove\"" in script


def test_cursor_preset_does_not_change_pointer():
    cfg = resolve_config("default", {"cursor_preset": "pointer"})
    script = get_cursor_init_script(cfg)
    assert 'fill="#fff"' in script
    assert "hexium-cursor-highlighter" not in script
