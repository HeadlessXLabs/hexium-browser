"""Hexium device-row sample → coerce → rewrite → validate, deterministic by seed."""

from __future__ import annotations

import random
from unittest.mock import patch

import pytest

from tests.persona_fixtures import linux_chrome_149_fingerprint, windows_chrome_147_fingerprint

from hexium_browser.persona.sample import sample_linux_chrome, sample_windows_chrome
from hexium_browser.persona.schema import CHROME_UA_VERSION
from hexium_browser.persona.validate import PersonaCoherenceError


def _fp_with_hw(cores: int) -> dict:
    return linux_chrome_149_fingerprint(navigator={"hardwareConcurrency": cores})


def test_sample_retries_until_validate_passes():
    bad = linux_chrome_149_fingerprint(
        navigator={"platform": "Win32", "userAgent": linux_chrome_149_fingerprint()["navigator"]["userAgent"]}
    )
    good = linux_chrome_149_fingerprint()
    with patch("hexium_browser.persona.sample._draw_linux_chrome", side_effect=[bad, good]):
        persona = sample_linux_chrome("seed-retry")
    assert persona["platform"] == "Linux x86_64"
    assert "151.0.7922.174" in persona["user_agent"]


def test_same_seed_is_deterministic():
    def draw():
        cores = 8 if random.random() < 0.5 else 16
        return _fp_with_hw(cores)

    with patch(
        "hexium_browser.persona.sample._draw_linux_chrome",
        side_effect=lambda *_a, **_k: draw(),
    ):
        a = sample_linux_chrome("fixed-seed")
        b = sample_linux_chrome("fixed-seed")
    assert a["hardware_concurrency"] == b["hardware_concurrency"]
    assert a["screen_width"] == b["screen_width"]
    assert a["device_memory_gb"] == b["device_memory_gb"]
    assert a["seed"] == b["seed"]


def test_sample_raises_after_ten_incoherent_draws():
    bad = linux_chrome_149_fingerprint(navigator={"platform": "Win32"})
    with patch("hexium_browser.persona.sample._draw_linux_chrome", return_value=bad):
        with patch("hexium_browser.persona.sample.MAX_DRAWS", 3):
            with pytest.raises(PersonaCoherenceError, match="after 3 draws"):
                sample_linux_chrome("doomed")


def test_real_linux_chrome_draw_is_coherent():
    a = sample_linux_chrome("hexium-network-seed")
    b = sample_linux_chrome("hexium-network-seed")
    assert a["platform"] not in {"Win32", "Win64"}
    assert a["ua_ch_platform"] != "Windows"
    assert "151.0.7922.174" in a["user_agent"]
    assert a["use_native_surfaces"] is True
    assert a["hardware_concurrency"] == b["hardware_concurrency"]
    assert a["screen_width"] == b["screen_width"]
    assert a["device_memory_gb"] == b["device_memory_gb"]


def test_windows_sample_retries_until_validate_passes():
    bad = windows_chrome_147_fingerprint(navigator={"platform": "Linux x86_64"})
    good = windows_chrome_147_fingerprint()
    with patch("hexium_browser.persona.sample._draw_windows_chrome", side_effect=[bad, good]):
        persona = sample_windows_chrome("seed-retry")
    assert persona["platform"] == "Win32"
    assert "151.0.7922.174" in persona["user_agent"]
    assert persona["use_native_surfaces"] is False


def test_windows_same_seed_is_deterministic():
    def draw():
        cores = 8 if random.random() < 0.5 else 16
        return windows_chrome_147_fingerprint(navigator={"hardwareConcurrency": cores})

    with patch(
        "hexium_browser.persona.sample._draw_windows_chrome",
        side_effect=lambda *_a, **_k: draw(),
    ):
        a = sample_windows_chrome("fixed-seed")
        b = sample_windows_chrome("fixed-seed")
    assert a["hardware_concurrency"] == b["hardware_concurrency"]
    assert a["screen_width"] == b["screen_width"]
    assert a["webgl_renderer"] == b["webgl_renderer"]
    assert a["seed"] == b["seed"]


def test_windows_sample_raises_after_ten_incoherent_draws():
    bad = windows_chrome_147_fingerprint(navigator={"platform": "Linux x86_64"})
    with patch("hexium_browser.persona.sample._draw_windows_chrome", return_value=bad):
        with patch("hexium_browser.persona.sample.MAX_DRAWS", 3):
            with pytest.raises(PersonaCoherenceError, match="after 3 draws"):
                sample_windows_chrome("doomed")


def test_real_windows_chrome_draw_is_coherent():
    a = sample_windows_chrome("hexium-windows-network-seed")
    b = sample_windows_chrome("hexium-windows-network-seed")
    assert a["platform"] in {"Win32", "Win64"}
    assert a["ua_ch_platform"] == "Windows"
    assert "151.0.7922.174" in a["user_agent"]
    assert a["use_native_surfaces"] is False
    assert "D3D11" in a["webgl_renderer"] or "Direct3D" in a["webgl_renderer"]
    assert a["ua_ch_platform_version"]
    assert a["hardware_concurrency"] == b["hardware_concurrency"]
    assert a["screen_width"] == b["screen_width"]
    assert a["webgl_renderer"] == b["webgl_renderer"]
    assert a["ua_ch_platform_version"] == b["ua_ch_platform_version"]


def test_real_linux_draw_is_rewritten_151_not_stale_major():
    persona = sample_linux_chrome("hexium-network-seed-140")
    assert CHROME_UA_VERSION in persona["user_agent"]
    assert "Chrome/39" not in persona["user_agent"]
    assert int(persona["hardware_concurrency"]) <= 32


def test_real_windows_draw_is_rewritten_151_not_stale_major():
    persona = sample_windows_chrome("hexium-windows-network-seed-140")
    assert CHROME_UA_VERSION in persona["user_agent"]
    assert persona["ua_ch_full_version"] == CHROME_UA_VERSION
    assert int(persona["hardware_concurrency"]) <= 32

