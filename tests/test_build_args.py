"""Unit tests for build_args timezone/locale injection and Hexium flags."""

from hexium_browser.browser import build_args, _resolve_timezone


def test_timezone_injected():
    args = build_args(stealth_args=True, extra_args=None, timezone="America/New_York")
    assert "--hexium-timezone=America/New_York" in args


def test_locale_injected():
    args = build_args(stealth_args=True, extra_args=None, locale="en-US")
    assert "--lang=en-US" in args
    assert "--hexium-locale=en-US,en" in args
    assert "--accept-lang=en-US,en" in args


def test_both_injected():
    args = build_args(
        stealth_args=True,
        extra_args=None,
        timezone="Europe/Berlin",
        locale="de-DE",
    )
    assert "--hexium-timezone=Europe/Berlin" in args
    assert "--lang=de-DE" in args
    assert "--hexium-locale=de-DE,de" in args
    assert "--accept-lang=de-DE,de" in args


def test_pakistan_locale_splits_chrome_pack_and_navigator():
    args = build_args(stealth_args=True, extra_args=None, locale="en-PK")
    assert "--lang=en-GB" in args
    assert "--hexium-locale=en-PK,en-GB,en" in args
    assert "--accept-lang=en-PK,en-GB,en" in args
    assert "--lang=en-PK" not in args


def test_timezone_independent_of_stealth_args():
    args = build_args(
        stealth_args=False,
        extra_args=None,
        timezone="America/New_York",
        locale="en-US",
    )
    assert "--hexium-timezone=America/New_York" in args
    assert "--lang=en-US" in args
    assert not any(a.startswith("--hexium-seed=") for a in args)


def test_no_flags_when_not_set(monkeypatch):
    monkeypatch.delenv("HEXIUM_ALLOW_3P_COOKIES", raising=False)
    args = build_args(stealth_args=True, extra_args=None)
    assert not any(a.startswith("--hexium-timezone=") for a in args)
    assert not any(a.startswith("--lang=") for a in args)
    assert not any(a.startswith("--hexium-locale=") for a in args)
    assert "--hexium-allow-3p-cookies" not in args


def test_fingerprint_off():
    args = build_args(stealth_args=True, extra_args=None, fingerprint="off")
    assert "--hexium-fingerprint=off" in args
    assert not any(a.startswith("--hexium-seed=") for a in args)


def test_fingerprint_seed():
    args = build_args(stealth_args=True, extra_args=None, fingerprint="test-seed")
    assert "--hexium-seed=test-seed" in args


def test_user_seed_overrides_default():
    args = build_args(stealth_args=True, extra_args=["--hexium-seed=99887"])
    seed_args = [a for a in args if a.startswith("--hexium-seed=")]
    assert len(seed_args) == 1
    assert seed_args[0] == "--hexium-seed=99887"


def test_user_persona_overrides_default():
    args = build_args(stealth_args=True, extra_args=["--hexium-persona=linux-native"])
    persona_args = [a for a in args if a.startswith("--hexium-persona=")]
    assert len(persona_args) == 1
    assert persona_args[0] == "--hexium-persona=linux-native"


def test_timezone_param_overrides_user_arg():
    args = build_args(
        stealth_args=True,
        extra_args=["--hexium-timezone=Europe/London"],
        timezone="America/New_York",
    )
    tz_args = [a for a in args if a.startswith("--hexium-timezone=")]
    assert tz_args == ["--hexium-timezone=America/New_York"]


def test_webrtc_ip_passed_through_args():
    args = build_args(stealth_args=True, extra_args=["--hexium-webrtc-ip=1.2.3.4"])
    assert "--hexium-webrtc-ip=1.2.3.4" in args


def test_resolve_timezone_id_alias():
    kwargs = {"timezone_id": "Europe/Paris"}
    result = _resolve_timezone(None, kwargs)
    assert result == "Europe/Paris"
    assert "timezone_id" not in kwargs


def test_start_maximized_injected_when_gated():
    args = build_args(stealth_args=True, extra_args=None, start_maximized=True)
    assert "--start-maximized" in args


def test_headed_linux_gets_gtk4(monkeypatch):
    monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.delenv("HEXIUM_NO_GTK4", raising=False)
    args = build_args(stealth_args=True, extra_args=None, headless=False)
    assert "--gtk-version=4" in args
    assert "--ozone-platform=x11" in args


def test_headless_skips_gtk4(monkeypatch):
    monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
    monkeypatch.setenv("DISPLAY", ":0")
    args = build_args(stealth_args=True, extra_args=None, headless=True)
    assert "--gtk-version=4" not in args
    assert "--ozone-platform=x11" not in args


def test_linux_headless_does_not_request_software_gl(monkeypatch):
    monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
    args = build_args(stealth_args=True, extra_args=None, headless=True)
    assert "--enable-unsafe-swiftshader" not in args
    assert "--disable-gpu" not in args
    assert not any(a.startswith("--use-gl=swiftshader") for a in args)
    assert "--ignore-gpu-blocklist" not in args


def test_linux_headed_requests_gpu_blocklist_bypass(monkeypatch):
    monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
    args = build_args(stealth_args=True, extra_args=None, headless=False)
    assert "--ignore-gpu-blocklist" in args


def test_user_gtk_arg_overrides_default(monkeypatch):
    monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.delenv("HEXIUM_NO_GTK4", raising=False)
    args = build_args(
        stealth_args=True,
        extra_args=["--gtk-version=3"],
        headless=False,
    )
    gtk = [a for a in args if a.startswith("--gtk-version=")]
    assert gtk == ["--gtk-version=3"]


def test_linux_headless_windows_chrome_enables_webgpu(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
    args = build_args(
        stealth_args=True,
        extra_args=["--hexium-persona=windows-chrome"],
        headless=True,
    )
    assert "--ignore-gpu-blocklist" in args
    assert "--enable-unsafe-webgpu" in args
    features = [a for a in args if a.startswith("--enable-features=")]
    assert any("Vulkan" in a for a in features)


def test_linux_native_headless_skips_forced_webgpu(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
    args = build_args(
        stealth_args=True,
        extra_args=None,
        headless=True,
    )
    assert "--hexium-persona=linux-native" in args or any(
        a.startswith("--hexium-persona=linux-native") for a in args
    )
    assert "--enable-unsafe-webgpu" not in args
    assert "--ignore-gpu-blocklist" not in args
    features = [a for a in args if a.startswith("--enable-features=")]
    assert not any("Vulkan" in a for a in features)


def test_linux_chrome_headless_skips_forced_webgpu(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
    args = build_args(
        stealth_args=True,
        extra_args=["--hexium-persona=linux-chrome"],
        headless=True,
    )
    assert "--enable-unsafe-webgpu" not in args


def test_fingerprint_off_skips_forced_webgpu(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("hexium_browser.config.platform.system", lambda: "Linux")
    args = build_args(
        stealth_args=True, extra_args=None, headless=True, fingerprint="off"
    )
    assert "--enable-unsafe-webgpu" not in args
