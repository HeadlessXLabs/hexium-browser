"""Coerce a BrowserForge Linux Chrome row into HexiumPersona JSON fields."""

from __future__ import annotations

from tests.persona_fixtures import linux_chrome_149_fingerprint, windows_chrome_147_fingerprint

from hexium_browser.persona.coerce import (
    coerce_fingerprint,
    load_persona_json,
    to_engine_json,
    write_persona_json,
)
from hexium_browser.persona.schema import CHROME_UA_VERSION


def test_coerce_maps_frozen_linux_fixture():
    persona = coerce_fingerprint(linux_chrome_149_fingerprint(), seed="seed-1")

    assert persona["user_agent_product"] == "Chrome"
    assert persona["platform"] == "Linux x86_64"
    assert persona["ua_ch_platform"] == "Linux"
    assert persona["screen_width"] == 1920
    assert persona["screen_height"] == 1080
    assert persona["screen_avail_width"] == 1920
    assert persona["screen_avail_height"] == 1040
    assert persona["color_depth"] == 24
    assert persona["device_pixel_ratio"] == 1.0
    assert persona["outer_height_delta"] == 88  # outerHeight 1040 - innerHeight 952
    assert persona["hardware_concurrency"] == 8
    assert persona["device_memory_gb"] == 8.0
    assert persona["audio_sample_rate"] == 48000.0
    assert persona["languages"] == ["en-US", "en"]
    assert persona["use_native_surfaces"] is True
    assert persona["spoofing_enabled"] is True
    assert persona["mask_webrtc_host_candidates"] is False
    assert persona["user_agent"] == linux_chrome_149_fingerprint()["navigator"]["userAgent"]
    assert persona["ua_ch_full_version"] == "149.0.7672.114"


def test_coerce_records_webgl_and_fonts_but_engine_json_omits_them():
    persona = coerce_fingerprint(linux_chrome_149_fingerprint(), seed="seed-1")
    assert "Intel" in persona["recorded_webgl_renderer"]
    assert "Noto Sans" in persona["recorded_fonts"]
    engine = to_engine_json(persona)
    assert "webgl_vendor" not in engine
    assert "webgl_renderer" not in engine
    assert "webgpu_vendor" not in engine
    assert "font_families" not in engine
    assert "system_ui_font" not in engine
    assert "recorded_webgl_renderer" not in engine
    assert "recorded_fonts" not in engine
    assert "user_agent" not in engine
    assert "ua_ch_full_version_list" not in engine
    assert engine["use_native_surfaces"] is True
    assert engine["platform"] == "Linux x86_64"
    assert engine["hardware_concurrency"] == 8
    assert "ua_ch_model" in engine


def test_coerce_hashes_seed_deterministically():
    a = coerce_fingerprint(linux_chrome_149_fingerprint(), seed="same")
    b = coerce_fingerprint(linux_chrome_149_fingerprint(), seed="same")
    c = coerce_fingerprint(linux_chrome_149_fingerprint(), seed="other")
    assert a["seed"] == b["seed"]
    assert a["seed"] != c["seed"]
    assert isinstance(a["seed"], int)


def test_engine_json_field_names_match_hexium_persona():
    persona = coerce_fingerprint(linux_chrome_149_fingerprint(), seed="seed-1")
    engine = to_engine_json(persona)
    expected = {
        "seed",
        "user_agent_product",
        "platform",
        "ua_ch_platform",
        "ua_ch_model",
        "languages",
        "timezone_id",
        "screen_width",
        "screen_height",
        "screen_avail_width",
        "screen_avail_height",
        "color_depth",
        "device_pixel_ratio",
        "outer_height_delta",
        "hardware_concurrency",
        "device_memory_gb",
        "audio_sample_rate",
        "use_native_surfaces",
        "spoofing_enabled",
        "mask_webrtc_host_candidates",
    }
    assert expected <= set(engine)
    assert CHROME_UA_VERSION  # imported for the rewrite contract in sibling tests


def test_windows_coerce_emits_gpu_fonts_and_disables_native_surfaces():
    persona = coerce_fingerprint(windows_chrome_147_fingerprint(), seed="seed-1")
    assert persona["platform"] == "Win32"
    assert persona["ua_ch_platform"] == "Windows"
    assert persona["use_native_surfaces"] is False
    assert persona["system_ui_font"] == "Segoe UI"
    assert "segoe ui" in [f.lower() for f in persona["font_families"]]
    assert "D3D11" in persona["webgl_renderer"]
    assert persona["webgl_vendor"] == "Google Inc. (NVIDIA)"
    assert persona["webgpu_vendor"] == "nvidia"
    assert persona["webgpu_architecture"]

    engine = to_engine_json(persona)
    assert engine["webgl_vendor"] == persona["webgl_vendor"]
    assert engine["webgl_renderer"] == persona["webgl_renderer"]
    assert engine["webgpu_vendor"] == "nvidia"
    assert engine["webgpu_architecture"] == persona["webgpu_architecture"]
    assert engine["font_families"] == persona["font_families"]
    assert engine["system_ui_font"] == "Segoe UI"
    assert engine["use_native_surfaces"] is False
    assert engine["ua_ch_platform_version"] == "10.0.0"
    assert "recorded_webgl_renderer" not in engine
    assert "recorded_fonts" not in engine


def test_windows_coerce_maps_intel_and_amd_webgpu_buckets():
    intel = coerce_fingerprint(
        windows_chrome_147_fingerprint(
            videoCard={
                "vendor": "Google Inc. (Intel)",
                "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            }
        ),
        seed="seed-1",
    )
    assert intel["webgpu_vendor"] == "intel"

    amd = coerce_fingerprint(
        windows_chrome_147_fingerprint(
            videoCard={
                "vendor": "Google Inc. (AMD)",
                "renderer": "ANGLE (AMD, AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
            }
        ),
        seed="seed-1",
    )
    assert amd["webgpu_vendor"] == "amd"


def test_windows_coerce_leaves_desktop_ua_ch_model_empty():
    persona = coerce_fingerprint(windows_chrome_147_fingerprint(), seed="seed-1")
    assert persona["ua_ch_model"] == ""


def test_windows_coerce_keeps_ua_ch_platform_version():
    win11 = coerce_fingerprint(windows_chrome_147_fingerprint(), seed="seed-1")
    assert win11["ua_ch_platform_version"] == "10.0.0"

    win10 = coerce_fingerprint(
        windows_chrome_147_fingerprint(
            navigator={"userAgentData": {"platformVersion": "10.0.0"}}
        ),
        seed="seed-1",
    )
    assert win10["ua_ch_platform_version"] == "10.0.0"

    contract19 = coerce_fingerprint(
        windows_chrome_147_fingerprint(
            navigator={"userAgentData": {"platformVersion": "19.0.0"}}
        ),
        seed="seed-1",
    )
    assert contract19["ua_ch_platform_version"] == "10.0.0"


def test_windows_coerce_bumps_half_gig_device_memory():
    persona = coerce_fingerprint(
        windows_chrome_147_fingerprint(navigator={"deviceMemory": 0.5}),
        seed="seed-1",
    )
    assert persona["device_memory_gb"] == 4.0


def test_coerce_repairs_mixed_physical_and_avail_screen():
    persona = coerce_fingerprint(
        windows_chrome_147_fingerprint(
            screen={
                "width": 2882,
                "height": 1922,
                "availWidth": 1264,
                "availHeight": 800,
                "colorDepth": 24,
                "devicePixelRatio": 1.0,
            }
        ),
        seed="seed-1",
    )
    assert persona["screen_width"] == 1264
    assert persona["screen_avail_width"] == 1264
    assert persona["screen_avail_height"] < persona["screen_height"]
    assert persona["screen_height"] - persona["screen_avail_height"] >= 40


def test_load_persona_json_roundtrip(tmp_path):
    persona = coerce_fingerprint(linux_chrome_149_fingerprint(), seed="seed-1")
    path = write_persona_json(persona, tmp_path)
    loaded = load_persona_json(tmp_path)
    assert loaded is not None
    assert loaded["fingerprint_seed"] == "seed-1"
    assert loaded["platform"] == "Linux x86_64"
    assert path == tmp_path / "persona.json"


def test_load_persona_json_missing(tmp_path):
    assert load_persona_json(tmp_path) is None


def test_load_persona_json_garbage(tmp_path):
    (tmp_path / "persona.json").write_text("{not json", encoding="utf-8")
    assert load_persona_json(tmp_path) is None


def test_linux_engine_json_still_omits_gpu_fonts_if_present():
    persona = coerce_fingerprint(linux_chrome_149_fingerprint(), seed="seed-1")
    persona["webgl_renderer"] = "should-not-leak"
    persona["font_families"] = ["Segoe UI"]
    persona["system_ui_font"] = "Segoe UI"
    engine = to_engine_json(persona)
    assert "webgl_renderer" not in engine
    assert "webgl_vendor" not in engine
    assert "webgpu_vendor" not in engine
    assert "font_families" not in engine
    assert "system_ui_font" not in engine
