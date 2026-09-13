"""Validate Linux Chrome 151 persona rows before the engine sees them."""

from __future__ import annotations

import pytest

from tests.persona_fixtures import linux_chrome_149_fingerprint, windows_chrome_147_fingerprint

from hexium_browser.persona.coerce import coerce_fingerprint
from hexium_browser.persona.rewrite_ua import rewrite_chrome_version
from hexium_browser.persona.schema import CHROME_UA_VERSION
from hexium_browser.persona.validate import (
    PersonaCoherenceError,
    validate_linux_chrome,
    validate_windows_chrome,
)


def _valid_persona(**overrides):
    raw = linux_chrome_149_fingerprint()
    persona = rewrite_chrome_version(coerce_fingerprint(raw, seed="seed-1"), CHROME_UA_VERSION)
    persona.update(overrides)
    return persona


def test_valid_linux_chrome_151_passes():
    validate_linux_chrome(_valid_persona())


def test_rejects_win32_platform():
    persona = _valid_persona(platform="Win32")
    with pytest.raises(PersonaCoherenceError, match="Win32"):
        validate_linux_chrome(persona)


def test_rejects_win64_platform():
    persona = _valid_persona(platform="Win64")
    with pytest.raises(PersonaCoherenceError, match="Win64"):
        validate_linux_chrome(persona)


def test_rejects_windows_ua_ch_platform():
    persona = _valid_persona(ua_ch_platform="Windows")
    with pytest.raises(PersonaCoherenceError, match="Windows"):
        validate_linux_chrome(persona)


def test_rejects_d3d11_renderer():
    persona = _valid_persona(
        recorded_webgl_renderer=(
            "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)"
        )
    )
    with pytest.raises(PersonaCoherenceError, match="Direct3D|D3D11"):
        validate_linux_chrome(persona)


def test_rejects_segoe_in_renderer():
    persona = _valid_persona(recorded_webgl_renderer="Segoe UI rasterizer")
    with pytest.raises(PersonaCoherenceError, match="Segoe"):
        validate_linux_chrome(persona)


def test_rejects_swiftshader():
    persona = _valid_persona(recorded_webgl_renderer="Google SwiftShader")
    with pytest.raises(PersonaCoherenceError, match="SwiftShader"):
        validate_linux_chrome(persona)


def test_rejects_llvmpipe():
    persona = _valid_persona(recorded_webgl_renderer="llvmpipe (LLVM 15.0.6)")
    with pytest.raises(PersonaCoherenceError, match="llvmpipe"):
        validate_linux_chrome(persona)


def test_rejects_microsoft_basic_render():
    persona = _valid_persona(
        recorded_webgl_renderer="Microsoft Basic Render Driver"
    )
    with pytest.raises(PersonaCoherenceError, match="Microsoft Basic Render"):
        validate_linux_chrome(persona)


def test_rejects_non_chrome_product():
    persona = _valid_persona(user_agent_product="Firefox")
    with pytest.raises(PersonaCoherenceError, match="Chrome"):
        validate_linux_chrome(persona)


def test_rejects_unrewritten_chrome_version():
    persona = _valid_persona(user_agent=linux_chrome_149_fingerprint()["navigator"]["userAgent"])
    with pytest.raises(PersonaCoherenceError, match="151.0.7922.174"):
        validate_linux_chrome(persona)


def test_rejects_mobile_screen():
    persona = _valid_persona(screen_width=390, screen_height=844)
    with pytest.raises(PersonaCoherenceError, match="mobile"):
        validate_linux_chrome(persona)


def test_rejects_segoe_calibri_only_font_list():
    persona = _valid_persona(recorded_fonts=["Segoe UI", "Calibri"])
    with pytest.raises(PersonaCoherenceError, match="Segoe|Calibri"):
        validate_linux_chrome(persona)


def test_rejects_384_hardware_concurrency():
    persona = _valid_persona(hardware_concurrency=384)
    with pytest.raises(PersonaCoherenceError, match="hardware_concurrency"):
        validate_linux_chrome(persona)


def test_rejects_zero_hardware_concurrency():
    persona = _valid_persona(hardware_concurrency=0)
    with pytest.raises(PersonaCoherenceError, match="hardware_concurrency"):
        validate_linux_chrome(persona)


def _valid_windows_persona(**overrides):
    raw = windows_chrome_147_fingerprint()
    persona = rewrite_chrome_version(coerce_fingerprint(raw, seed="seed-1"), CHROME_UA_VERSION)
    persona.update(overrides)
    return persona


def test_valid_windows_chrome_151_passes():
    validate_windows_chrome(_valid_windows_persona())


def test_windows_rejects_contract_platform_version():
    persona = _valid_windows_persona(ua_ch_platform_version="19.0.0")
    with pytest.raises(PersonaCoherenceError, match="10.0.0|15.0.0"):
        validate_windows_chrome(persona)


def test_windows_rejects_linux_platform():
    persona = _valid_windows_persona(platform="Linux x86_64")
    with pytest.raises(PersonaCoherenceError, match="Linux"):
        validate_windows_chrome(persona)


def test_windows_rejects_linux_ua_ch_platform():
    persona = _valid_windows_persona(ua_ch_platform="Linux")
    with pytest.raises(PersonaCoherenceError, match="Linux"):
        validate_windows_chrome(persona)


def test_windows_requires_win32_or_win64():
    persona = _valid_windows_persona(platform="MacIntel")
    with pytest.raises(PersonaCoherenceError, match="Win32|Windows"):
        validate_windows_chrome(persona)


def test_windows_rejects_mesa_renderer():
    mesa = "ANGLE (Intel, Mesa Intel(R) UHD Graphics 630 (CFL GT2), OpenGL 4.6)"
    persona = _valid_windows_persona(recorded_webgl_renderer=mesa, webgl_renderer=mesa)
    with pytest.raises(PersonaCoherenceError, match="Mesa|OpenGL"):
        validate_windows_chrome(persona)


def test_windows_rejects_swiftshader():
    persona = _valid_windows_persona(
        recorded_webgl_renderer="Google SwiftShader",
        webgl_renderer="Google SwiftShader",
    )
    with pytest.raises(PersonaCoherenceError, match="SwiftShader"):
        validate_windows_chrome(persona)


def test_windows_rejects_microsoft_basic_render():
    persona = _valid_windows_persona(
        recorded_webgl_renderer="Microsoft Basic Render Driver",
        webgl_renderer="Microsoft Basic Render Driver",
    )
    with pytest.raises(PersonaCoherenceError, match="Microsoft Basic Render"):
        validate_windows_chrome(persona)


def test_windows_requires_d3d11_renderer():
    persona = _valid_windows_persona(
        recorded_webgl_renderer="ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER, Vulkan)",
        webgl_renderer="ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER, Vulkan)",
    )
    with pytest.raises(PersonaCoherenceError, match="D3D11|Direct3D"):
        validate_windows_chrome(persona)


def test_windows_rejects_unrewritten_chrome_version():
    persona = _valid_windows_persona(
        user_agent=windows_chrome_147_fingerprint()["navigator"]["userAgent"]
    )
    with pytest.raises(PersonaCoherenceError, match="151.0.7922.174"):
        validate_windows_chrome(persona)


def test_windows_rejects_mobile_ua():
    persona = _valid_windows_persona(
        user_agent=(
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{CHROME_UA_VERSION} Mobile Safari/537.36"
        )
    )
    with pytest.raises(PersonaCoherenceError, match="mobile"):
        validate_windows_chrome(persona)


def test_windows_rejects_mobile_screen():
    persona = _valid_windows_persona(screen_width=390, screen_height=844)
    with pytest.raises(PersonaCoherenceError, match="mobile"):
        validate_windows_chrome(persona)


def test_windows_requires_segoe_or_pack_fonts():
    persona = _valid_windows_persona(recorded_fonts=["Arial", "Times New Roman"], font_families=[])
    with pytest.raises(PersonaCoherenceError, match="Segoe"):
        validate_windows_chrome(persona)


def test_windows_accepts_pack_backed_segoe_font_families():
    persona = _valid_windows_persona(
        recorded_fonts=["Arial"],
        font_families=["segoe ui", "arial", "calibri"],
    )
    validate_windows_chrome(persona)


def test_windows_rejects_384_hardware_concurrency():
    persona = _valid_windows_persona(hardware_concurrency=384)
    with pytest.raises(PersonaCoherenceError, match="hardware_concurrency"):
        validate_windows_chrome(persona)
