"""Unit tests for GeoIP-based timezone/locale detection."""

import inspect
from unittest.mock import MagicMock, patch
import threading
import time

import pytest

from hexium_browser.browser import (
    launch,
    launch_async,
    launch_context,
    launch_context_async,
    launch_persistent_context,
    launch_persistent_context_async,
    maybe_resolve_geoip,
)
from hexium_browser.geoip import (
    COUNTRY_LOCALE_MAP,
    bcp47_to_posix_locale,
    normalize_chrome_locale,
    _is_private_ip,
    _resolve_exit_ip,
    _resolve_proxy_ip,
)


# ---------------------------------------------------------------------------
# _resolve_proxy_ip
# ---------------------------------------------------------------------------


def test_resolve_literal_ipv4():
    assert _resolve_proxy_ip("http://10.50.96.5:8888") == "10.50.96.5"


def test_resolve_literal_ipv4_with_auth():
    assert _resolve_proxy_ip("http://user:pass@10.50.96.5:8888") == "10.50.96.5"


def test_resolve_literal_ipv6():
    ip = _resolve_proxy_ip("http://[::1]:8888")
    assert ip == "::1"


def test_resolve_hostname():
    """DNS resolution of a known hostname should return an IP."""
    ip = _resolve_proxy_ip("http://localhost:8888")
    assert ip is not None
    assert ip in ("127.0.0.1", "::1")


def test_resolve_invalid_url():
    assert _resolve_proxy_ip("not-a-url") is None


def test_resolve_empty():
    assert _resolve_proxy_ip("") is None


# ---------------------------------------------------------------------------
# COUNTRY_LOCALE_MAP
# ---------------------------------------------------------------------------


def test_locale_map_has_common_countries():
    for code in ("US", "GB", "DE", "FR", "JP", "BR", "IL", "RU"):
        assert code in COUNTRY_LOCALE_MAP, f"Missing {code}"


def test_locale_map_values_are_bcp47():
    """All locales should be language-REGION format."""
    for code, locale in COUNTRY_LOCALE_MAP.items():
        parts = locale.split("-")
        assert len(parts) == 2, f"{code}: {locale} not language-REGION"
        assert parts[0].islower(), f"{code}: language part should be lowercase"
        assert parts[1].isupper(), f"{code}: region part should be uppercase"


def test_pakistan_keeps_region_tag_and_chrome_pack():
    from hexium_browser.geoip import chrome_lang_for_locale
    from hexium_browser.persona.geo_overlay import languages_from_locale

    assert COUNTRY_LOCALE_MAP["PK"] == "en-PK"
    assert chrome_lang_for_locale("en-PK") == "en-GB"
    assert normalize_chrome_locale("en-PK") == "en-GB"
    assert normalize_chrome_locale("en-US") == "en-US"
    assert normalize_chrome_locale("de-DE") == "de-DE"
    assert languages_from_locale("en-PK") == ["en-PK", "en-GB", "en"]
    assert languages_from_locale("de-DE") == ["de-DE", "de"]
    assert languages_from_locale("en-GB") == ["en-GB", "en"]


def test_bcp47_to_posix_locale():
    assert bcp47_to_posix_locale("en-GB") == "en_GB.UTF-8"


# ---------------------------------------------------------------------------
# resolve_proxy_geo fallbacks
# ---------------------------------------------------------------------------


def test_resolve_geo_continues_when_geoip2_missing():
    """Missing geoip2 must not abort launch — still return the exit IP for WebRTC."""
    with patch.dict("sys.modules", {"geoip2": None, "geoip2.database": None}):
        from importlib import reload
        import hexium_browser.geoip as geoip_mod
        reload(geoip_mod)
        with patch.object(geoip_mod, "_resolve_exit_ip", return_value="9.8.7.6"):
            assert geoip_mod.resolve_proxy_geo_with_ip("http://10.50.96.5:8888") == (
                None,
                None,
                "9.8.7.6",
            )
        reload(geoip_mod)


def test_resolve_geo_returns_none_when_db_missing():
    """Should return (None, None) when DB file doesn't exist."""
    mock_geoip2 = type("module", (), {"database": type("db", (), {"Reader": None})})()
    with patch.dict("sys.modules", {"geoip2": mock_geoip2, "geoip2.database": mock_geoip2.database}):
        with patch("hexium_browser.geoip._ensure_geoip_db", return_value=None):
            with patch("hexium_browser.geoip._resolve_exit_ip", return_value=None):
                from hexium_browser.geoip import resolve_proxy_geo
                assert resolve_proxy_geo("http://10.50.96.5:8888") == (None, None)


def test_resolve_geo_keeps_exit_ip_when_db_missing():
    """DB missing but IP resolvable → still return the exit IP for WebRTC spoofing.

    Resolving the egress IP does not need the GeoIP DB, so a DB download failure
    must not drop it — otherwise WebRTC could fall back to the real IP behind a
    proxy while the connection shows the proxy IP (a deanonymization).
    """
    mock_geoip2 = type("module", (), {"database": type("db", (), {"Reader": None})})()
    with patch.dict("sys.modules", {"geoip2": mock_geoip2, "geoip2.database": mock_geoip2.database}):
        with patch("hexium_browser.geoip._ensure_geoip_db", return_value=None):
            with patch("hexium_browser.geoip._resolve_exit_ip", return_value="9.8.7.6"):
                from hexium_browser.geoip import resolve_proxy_geo_with_ip
                assert resolve_proxy_geo_with_ip("http://10.50.96.5:8888") == (None, None, "9.8.7.6")


# ---------------------------------------------------------------------------
# _resolve_exit_ip direct (no-proxy) fetch
# ---------------------------------------------------------------------------


def test_resolve_exit_ip_no_proxy_fetches_directly():
    """No proxy → echo services queried directly (proxy=None)."""
    resp = MagicMock()
    resp.text = "5.6.7.8"
    resp.raise_for_status = MagicMock()
    with patch("httpx.get", return_value=resp) as mock_get:
        ip = _resolve_exit_ip(None)
    assert ip == "5.6.7.8"
    # httpx.get called with proxy=None (direct), not through a proxy
    assert mock_get.call_args.kwargs.get("proxy") is None


# ---------------------------------------------------------------------------
# maybe_resolve_geoip (browser.py helper)
# ---------------------------------------------------------------------------


def test_maybe_resolve_skips_when_geoip_false():
    tz, loc, ip = maybe_resolve_geoip(False, "http://proxy:8080", None, None)
    assert tz is None
    assert loc is None
    assert ip is None


def test_maybe_resolve_no_proxy_uses_machine_ip():
    """With no proxy, geoip resolves the machine's own public IP for tz/locale."""
    with patch(
        "hexium_browser.geoip.resolve_proxy_geo_with_ip",
        return_value=("Europe/Berlin", "de-DE", "5.6.7.8"),
    ) as m:
        tz, loc, ip = maybe_resolve_geoip(True, None, None, None)
    # Called with proxy_url=None → echo services resolve machine IP
    m.assert_called_once_with(None)
    assert tz == "Europe/Berlin"
    assert loc == "de-DE"
    assert ip == "5.6.7.8"  # drives --hexium-webrtc-ip


def test_maybe_resolve_no_proxy_both_explicit_skips_ip():
    """No proxy + explicit tz/locale → skip the exit-IP fetch entirely.

    With no proxy the WebRTC IP would just be the real connection IP the site
    already sees (a no-op), so we don't make a third-party echo call.
    """
    with patch(
        "hexium_browser.geoip.resolve_proxy_exit_ip", return_value="5.6.7.8"
    ) as m:
        tz, loc, ip = maybe_resolve_geoip(True, None, "Europe/Berlin", "de-DE")
    m.assert_not_called()
    assert tz == "Europe/Berlin"
    assert loc == "de-DE"
    assert ip is None


def test_maybe_resolve_skips_when_both_explicit():
    """Explicit values should still resolve exit IP for WebRTC."""
    with patch("hexium_browser.geoip._resolve_exit_ip", return_value="1.2.3.4"):
        tz, loc, ip = maybe_resolve_geoip(True, "http://proxy:8080", "Europe/Berlin", "de-DE")
    assert tz == "Europe/Berlin"
    assert loc == "de-DE"
    assert ip == "1.2.3.4"


def test_maybe_resolve_fills_missing_timezone():
    """When only locale is explicit, geoip should fill timezone."""
    with patch("hexium_browser.geoip.resolve_proxy_geo_with_ip", return_value=("America/New_York", "en-US", "1.2.3.4")):
        tz, loc, ip = maybe_resolve_geoip(True, "http://proxy:8080", None, "fr-FR")
        assert tz == "America/New_York"
        assert loc == "fr-FR"  # Explicit wins


def test_maybe_resolve_fills_missing_locale():
    """When only timezone is explicit, geoip should fill locale."""
    with patch("hexium_browser.geoip.resolve_proxy_geo_with_ip", return_value=("America/New_York", "en-US", "1.2.3.4")):
        tz, loc, ip = maybe_resolve_geoip(True, "http://proxy:8080", "Asia/Tokyo", None)
        assert tz == "Asia/Tokyo"  # Explicit wins
        assert loc == "en-US"


def test_maybe_resolve_fills_both():
    """When neither is set, geoip should fill both."""
    with patch("hexium_browser.geoip.resolve_proxy_geo_with_ip", return_value=("Europe/Berlin", "de-DE", "5.6.7.8")):
        tz, loc, ip = maybe_resolve_geoip(True, "http://proxy:8080", None, None)
        assert tz == "Europe/Berlin"
        assert loc == "de-DE"
        assert ip == "5.6.7.8"


def test_maybe_resolve_raw_timezone_flag_wins_over_geoip():
    """A raw --hexium-timezone in args counts as explicit; geoip must not clobber it."""
    with patch(
        "hexium_browser.geoip.resolve_proxy_geo_with_ip",
        return_value=("Europe/Berlin", "de-DE", "5.6.7.8"),
    ):
        tz, loc, ip = maybe_resolve_geoip(
            True, "http://proxy:8080", None, None,
            ["--hexium-timezone=Asia/Tokyo"],
        )
    assert tz == "Asia/Tokyo"  # user's raw flag survives
    assert loc == "de-DE"  # not raw-flagged → geoip fills it
    assert ip == "5.6.7.8"


def test_maybe_resolve_raw_lang_flag_wins_over_geoip():
    """A raw --lang in args counts as explicit locale; geoip must not clobber it."""
    with patch(
        "hexium_browser.geoip.resolve_proxy_geo_with_ip",
        return_value=("Europe/Berlin", "de-DE", "5.6.7.8"),
    ):
        tz, loc, ip = maybe_resolve_geoip(
            True, "http://proxy:8080", None, None, ["--lang=fr-FR"],
        )
    assert tz == "Europe/Berlin"  # not raw-flagged → geoip fills it
    assert loc == "fr-FR"  # user's raw flag survives


def test_maybe_resolve_raw_flags_both_skip_geo_lookup():
    """Both tz+locale raw-flagged → treated as fully explicit, only exit IP resolved."""
    with patch("hexium_browser.geoip.resolve_proxy_geo_with_ip") as geo, patch(
        "hexium_browser.geoip._resolve_exit_ip", return_value="1.2.3.4"
    ):
        tz, loc, ip = maybe_resolve_geoip(
            True, "http://proxy:8080", None, None,
            ["--hexium-timezone=Asia/Tokyo", "--hexium-locale=ja-JP"],
        )
    geo.assert_not_called()
    assert tz == "Asia/Tokyo"
    assert loc == "ja-JP"
    assert ip == "1.2.3.4"


def test_maybe_resolve_param_beats_raw_flag():
    """An explicit timezone= param takes precedence over a differing raw flag."""
    with patch("hexium_browser.geoip._resolve_exit_ip", return_value="1.2.3.4"), patch(
        "hexium_browser.geoip.resolve_proxy_geo_with_ip",
        return_value=("Europe/Berlin", "de-DE", "5.6.7.8"),
    ):
        tz, loc, ip = maybe_resolve_geoip(
            True, "http://proxy:8080", "America/New_York", None,
            ["--hexium-timezone=Asia/Tokyo"],
        )
    assert tz == "America/New_York"  # param wins over raw flag
    assert loc == "de-DE"


def test_maybe_resolve_geoip_timeout_returns_existing_values(monkeypatch):
    """A stalled proxy lookup should not block launch indefinitely."""
    mock_geoip2 = type("module", (), {"database": type("db", (), {"Reader": None})})()
    monkeypatch.setenv("HEXIUM_GEOIP_TIMEOUT_SECONDS", "0.05")
    with patch.dict("sys.modules", {"geoip2": mock_geoip2, "geoip2.database": mock_geoip2.database}):
        with patch("hexium_browser.geoip._ensure_geoip_db", return_value=object()):
            start = time.monotonic()
            tz, loc, ip = maybe_resolve_geoip(True, "http://203.0.113.10:8080", None, "fr-FR")
            elapsed = time.monotonic() - start

    assert (tz, loc, ip) == (None, "fr-FR", None)
    assert elapsed < 0.5


# ---------------------------------------------------------------------------
# _is_private_ip
# ---------------------------------------------------------------------------


def test_private_ip_loopback():
    assert _is_private_ip("127.0.0.1") is True


def test_private_ip_rfc1918():
    assert _is_private_ip("192.168.1.1") is True
    assert _is_private_ip("10.0.0.1") is True
    assert _is_private_ip("172.16.0.1") is True


def test_private_ip_public():
    assert _is_private_ip("8.8.8.8") is False
    assert _is_private_ip("64.176.168.43") is False


# ---------------------------------------------------------------------------
# GeoIP DB download: atomic replace + concurrency guard (issue #458)
# ---------------------------------------------------------------------------


def test_download_overwrites_existing_db(tmp_path):
    """os.replace must overwrite a pre-existing DB (Windows rename would fail)."""
    from hexium_browser import geoip

    dest = tmp_path / "GeoLite2-City.mmdb"
    dest.write_bytes(b"old")

    def fake_stream(*_a, **_k):
        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def raise_for_status(self):
                pass

            headers = {"content-length": "3"}

            def iter_bytes(self, chunk_size=0):
                yield b"new"

        return _Resp()

    with patch("httpx.stream", fake_stream):
        geoip._download_geoip_db(dest)

    assert dest.read_bytes() == b"new"


def test_ensure_db_downloads_once_under_concurrency(tmp_path):
    """Concurrent first-use launches must trigger only one download."""
    from hexium_browser import geoip

    dest = tmp_path / "GeoLite2-City.mmdb"
    calls = []
    barrier = threading.Barrier(5)

    def fake_download(path):
        calls.append(path)
        time.sleep(0.05)  # hold the lock so others queue behind it
        path.write_bytes(b"db")

    with patch.object(geoip, "_get_geoip_dir", return_value=tmp_path), patch.object(
        geoip, "_download_geoip_db", side_effect=fake_download
    ):
        results = []

        def worker():
            barrier.wait()
            results.append(geoip._ensure_geoip_db())

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert len(calls) == 1  # only one thread actually downloaded
    assert all(r == dest for r in results)


# ---------------------------------------------------------------------------
# launch APIs default geoip=True
# ---------------------------------------------------------------------------


_LAUNCH_FNS = (
    launch,
    launch_async,
    launch_persistent_context,
    launch_persistent_context_async,
    launch_context,
    launch_context_async,
)


def _make_mock_pw_and_context():
    context = MagicMock()
    pw = MagicMock()
    pw.chromium.launch_persistent_context.return_value = context
    pw_cm = MagicMock()
    pw_cm.start.return_value = pw
    return pw_cm, pw, context


@pytest.mark.parametrize("fn", _LAUNCH_FNS, ids=lambda f: f.__name__)
def test_launch_geoip_default_is_true(fn):
    assert inspect.signature(fn).parameters["geoip"].default is True


@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, None, None))
def test_launch_persistent_omitted_geoip_passes_true(mock_geoip, _mock_bin, tmp_path, monkeypatch):
    """Not passing geoip= still enables lookup (default True)."""
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    monkeypatch.delenv("HEXIUM_PROFILES_DIR", raising=False)
    pw_cm, _pw, _context = _make_mock_pw_and_context()

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        launch_persistent_context(tmp_path / "profile", humanize=False)

    mock_geoip.assert_called()
    assert mock_geoip.call_args.args[0] is True


@patch("hexium_browser.geoip.resolve_proxy_geo_with_ip", return_value=("Europe/Berlin", "de-DE", "5.6.7.8"))
@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
def test_launch_persistent_geoip_false_does_not_fill(_mock_bin, mock_geo, tmp_path, monkeypatch):
    """geoip=False is the opt-out: skip lookup, do not fill tz/locale."""
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    monkeypatch.delenv("HEXIUM_PROFILES_DIR", raising=False)
    pw_cm, pw, _context = _make_mock_pw_and_context()

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        launch_persistent_context(tmp_path / "profile", humanize=False, geoip=False)

    mock_geo.assert_not_called()
    chrome_args = pw.chromium.launch_persistent_context.call_args.kwargs["args"]
    assert not any(a.startswith("--hexium-timezone=") for a in chrome_args)
    assert "--lang=de-DE" not in chrome_args


@patch("hexium_browser.geoip.resolve_proxy_geo_with_ip", return_value=("Europe/Berlin", "de-DE", None))
@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
def test_explicit_timezone_wins_with_default_geoip(_mock_bin, _mock_geo, tmp_path, monkeypatch):
    """Explicit timezone= still wins when geoip defaults on."""
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    monkeypatch.delenv("HEXIUM_PROFILES_DIR", raising=False)
    pw_cm, pw, _context = _make_mock_pw_and_context()

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        launch_persistent_context(
            tmp_path / "profile", humanize=False, timezone="Asia/Tokyo"
        )

    chrome_args = pw.chromium.launch_persistent_context.call_args.kwargs["args"]
    assert "--hexium-timezone=Asia/Tokyo" in chrome_args
    assert "--hexium-timezone=Europe/Berlin" not in chrome_args
    assert "--lang=de-DE" in chrome_args


@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, "en-GB", None))
def test_launch_persistent_pins_lang_env(mock_geoip, _mock_bin, tmp_path, monkeypatch):
    """LANG/LC_ALL follow --lang so Intl cannot leak the host locale."""
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    monkeypatch.delenv("HEXIUM_PROFILES_DIR", raising=False)
    pw_cm, pw, _context = _make_mock_pw_and_context()

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        launch_persistent_context(tmp_path / "profile", humanize=False, locale="en-GB")

    env = pw.chromium.launch_persistent_context.call_args.kwargs["env"]
    assert env["LANG"] == "en_GB.UTF-8"
    assert env["LC_ALL"] == "en_GB.UTF-8"


@patch("hexium_browser.browser.ensure_binary", return_value="/fake/chrome")
@patch("hexium_browser.browser.maybe_resolve_geoip", return_value=(None, "en-PK", None))
def test_launch_persistent_pk_locale_uses_gb_pack(mock_geoip, _mock_bin, tmp_path, monkeypatch):
    """en-PK is navigator/Accept-Language; --lang and LANG stay the en-GB pack."""
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    monkeypatch.delenv("HEXIUM_PROFILES_DIR", raising=False)
    pw_cm, pw, _context = _make_mock_pw_and_context()

    with patch("playwright.sync_api.sync_playwright", return_value=pw_cm):
        launch_persistent_context(tmp_path / "profile", humanize=False, locale="en-PK")

    chrome_args = pw.chromium.launch_persistent_context.call_args.kwargs["args"]
    env = pw.chromium.launch_persistent_context.call_args.kwargs["env"]
    assert "--lang=en-GB" in chrome_args
    assert "--hexium-locale=en-PK,en-GB,en" in chrome_args
    assert "--accept-lang=en-PK,en-GB,en" in chrome_args
    assert env["LANG"] == "en_GB.UTF-8"
    assert env["LC_ALL"] == "en_GB.UTF-8"


# ---------------------------------------------------------------------------
# apply_geoip (persona overlay — after sample, locale/tz/webrtc only)
# ---------------------------------------------------------------------------


def test_apply_geoip_changes_only_tz_languages_webrtc():
    from hexium_browser.persona.coerce import coerce_fingerprint
    from hexium_browser.persona.geo_overlay import apply_geoip
    from tests.persona_fixtures import linux_chrome_149_fingerprint

    persona = coerce_fingerprint(linux_chrome_149_fingerprint(), seed="geo")
    before = {
        "hardware_concurrency": persona["hardware_concurrency"],
        "screen_width": persona["screen_width"],
        "device_memory_gb": persona["device_memory_gb"],
        "platform": persona["platform"],
        "ua_ch_model": persona["ua_ch_model"],
        "audio_sample_rate": persona["audio_sample_rate"],
        "recorded_webgl_renderer": persona["recorded_webgl_renderer"],
    }
    apply_geoip(
        persona,
        timezone="Europe/Berlin",
        locale="de-DE",
        exit_ip="5.6.7.8",
    )
    assert persona["timezone_id"] == "Europe/Berlin"
    assert persona["languages"][0] == "de-DE"
    assert persona["languages"] == ["de-DE", "de"]
    assert persona["webrtc_mask_ip"] == "5.6.7.8"
    assert persona["mask_webrtc_host_candidates"] is True
    for key, value in before.items():
        assert persona[key] == value


def test_apply_geoip_pakistan_languages_keep_region_tag():
    from hexium_browser.persona.coerce import coerce_fingerprint
    from hexium_browser.persona.geo_overlay import apply_geoip
    from tests.persona_fixtures import linux_chrome_149_fingerprint

    persona = coerce_fingerprint(linux_chrome_149_fingerprint(), seed="geo-pk")
    apply_geoip(persona, timezone="Asia/Karachi", locale="en-PK")
    assert persona["languages"] == ["en-PK", "en-GB", "en"]
    assert persona["timezone_id"] == "Asia/Karachi"


def test_apply_geoip_none_fields_leave_sampled_values():
    from hexium_browser.persona.coerce import coerce_fingerprint
    from hexium_browser.persona.geo_overlay import apply_geoip
    from tests.persona_fixtures import linux_chrome_149_fingerprint

    persona = coerce_fingerprint(linux_chrome_149_fingerprint(), seed="geo")
    original_tz = persona["timezone_id"]
    original_langs = list(persona["languages"])
    apply_geoip(persona, timezone=None, locale=None, exit_ip=None)
    assert persona["timezone_id"] == original_tz
    assert persona["languages"] == original_langs
    assert persona["mask_webrtc_host_candidates"] is False
    assert not persona.get("webrtc_mask_ip")
