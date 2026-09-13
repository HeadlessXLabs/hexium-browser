"""HX-P4-04: optional --hexium-allow-3p-cookies (default off)."""

from hexium_browser.browser import build_args
from hexium_browser.config import allow_3p_cookies_enabled


def test_allow_3p_cookies_default_off(monkeypatch):
    monkeypatch.delenv("HEXIUM_ALLOW_3P_COOKIES", raising=False)
    assert allow_3p_cookies_enabled() is False
    args = build_args(stealth_args=True, extra_args=None)
    assert "--hexium-allow-3p-cookies" not in args


def test_allow_3p_cookies_kwarg_on(monkeypatch):
    monkeypatch.delenv("HEXIUM_ALLOW_3P_COOKIES", raising=False)
    args = build_args(stealth_args=True, extra_args=None, allow_3p_cookies=True)
    assert "--hexium-allow-3p-cookies" in args


def test_allow_3p_cookies_env_on(monkeypatch):
    monkeypatch.setenv("HEXIUM_ALLOW_3P_COOKIES", "1")
    assert allow_3p_cookies_enabled() is True
    args = build_args(stealth_args=True, extra_args=None)
    assert "--hexium-allow-3p-cookies" in args


def test_allow_3p_cookies_kwarg_false_overrides_env(monkeypatch):
    monkeypatch.setenv("HEXIUM_ALLOW_3P_COOKIES", "1")
    assert allow_3p_cookies_enabled(False) is False
    args = build_args(stealth_args=True, extra_args=None, allow_3p_cookies=False)
    assert "--hexium-allow-3p-cookies" not in args


def test_allow_3p_cookies_via_extra_args(monkeypatch):
    monkeypatch.delenv("HEXIUM_ALLOW_3P_COOKIES", raising=False)
    args = build_args(
        stealth_args=True, extra_args=["--hexium-allow-3p-cookies"]
    )
    assert "--hexium-allow-3p-cookies" in args


def test_allow_3p_cookies_env_truthy_aliases(monkeypatch):
    for value in ("true", "yes", "on", "TRUE"):
        monkeypatch.setenv("HEXIUM_ALLOW_3P_COOKIES", value)
        assert allow_3p_cookies_enabled() is True
    monkeypatch.setenv("HEXIUM_ALLOW_3P_COOKIES", "0")
    assert allow_3p_cookies_enabled() is False
