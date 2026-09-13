"""Tests for proxy URL parsing and credential extraction."""

from unittest.mock import patch

from hexium_browser.browser import (
    _is_socks_proxy,
    _parse_proxy_url,
    _resolve_proxy_config,
    maybe_resolve_geoip,
)

PROXY_NET = [
    "--hexium-proxy=1",
    "--disable-http2",
    "--disable-quic",
    "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
]


def _assert_proxy_network_args(args: list[str]) -> None:
    for flag in PROXY_NET:
        assert flag in args


class TestParseProxyUrl:
    def test_no_credentials(self):
        assert _parse_proxy_url("http://proxy:8080") == {"server": "http://proxy:8080"}

    def test_with_credentials(self):
        result = _parse_proxy_url("http://user:pass@proxy:8080")
        assert result == {"server": "http://proxy:8080", "username": "user", "password": "pass"}

    def test_url_encoded_password(self):
        result = _parse_proxy_url("http://user:p%40ss%3Aword@proxy:8080")
        assert result["password"] == "p@ss:word"
        assert result["username"] == "user"
        assert result["server"] == "http://proxy:8080"

    def test_socks5(self):
        result = _parse_proxy_url("socks5://user:pass@proxy:1080")
        assert result["server"] == "socks5://proxy:1080"
        assert result["username"] == "user"
        assert result["password"] == "pass"

    def test_no_port(self):
        result = _parse_proxy_url("http://user:pass@proxy")
        assert result["server"] == "http://proxy"
        assert result["username"] == "user"

    def test_username_only(self):
        result = _parse_proxy_url("http://user@proxy:8080")
        assert result["server"] == "http://proxy:8080"
        assert result["username"] == "user"
        assert "password" not in result


class TestBuildProxyKwargs:
    """Tests for _resolve_proxy_config (formerly _build_proxy_kwargs) HTTP path."""

    def test_none(self):
        kwargs, args = _resolve_proxy_config(None)
        assert kwargs == {}
        assert args == []

    def test_simple_proxy(self):
        kwargs, args = _resolve_proxy_config("http://proxy:8080")
        assert kwargs == {"proxy": {"server": "http://proxy:8080"}}
        _assert_proxy_network_args(args)

    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_proxy_with_auth(self, *_):
        kwargs, args = _resolve_proxy_config("http://user:pass@proxy:8080")
        _assert_proxy_network_args(args)
        assert kwargs == {
            "proxy": {"server": "http://proxy:8080", "username": "user", "password": "pass"}
        }

    @patch("hexium_browser.config._http_proxy_inline_auth_enabled", return_value=True)
    @patch("hexium_browser.config.get_chromium_version", return_value="151.0.7922.174.1")
    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_proxy_with_auth_inline_when_opt_in(self, *_):
        kwargs, args = _resolve_proxy_config("http://user:pass@proxy:8080")
        assert kwargs == {}
        assert args == ["--proxy-server=http://user:pass@proxy:8080", *PROXY_NET]

    def test_proxy_dict_passthrough(self):
        proxy_dict = {"server": "http://proxy:8080", "bypass": ".google.com,localhost"}
        kwargs, args = _resolve_proxy_config(proxy_dict)
        assert kwargs == {"proxy": proxy_dict}
        _assert_proxy_network_args(args)

    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_pinned_old_version_disables_inline_auth(self, _mock):
        # Pin a binary BELOW the inline-auth floor (146.0.7680.177.5) on a
        # platform that otherwise supports it. The gate must read the pin — an
        # older binary lacks inline proxy auth — and fall back to Playwright's
        # dict, else rolled-back binaries break proxy auth (#182).
        kwargs, args = _resolve_proxy_config(
            "http://user:pass@proxy:8080", browser_version="146.0.7680.177.3"
        )
        _assert_proxy_network_args(args)
        assert kwargs == {"proxy": {"server": "http://proxy:8080", "username": "user", "password": "pass"}}

    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_pinned_new_version_keeps_playwright_fallback_until_patch(self, *_):
        kwargs, args = _resolve_proxy_config(
            "http://user:pass@proxy:8080", browser_version="151.0.7922.174.1"
        )
        _assert_proxy_network_args(args)
        assert kwargs == {
            "proxy": {"server": "http://proxy:8080", "username": "user", "password": "pass"}
        }

    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_proxy_dict_with_auth(self, *_):
        proxy_dict = {
            "server": "http://proxy:8080",
            "username": "user",
            "password": "pass",
            "bypass": ".example.com",
        }
        kwargs, args = _resolve_proxy_config(proxy_dict)
        assert kwargs == {"proxy": proxy_dict}
        _assert_proxy_network_args(args)


class TestMaybeResolveGeoip:
    @patch("hexium_browser.geoip.resolve_proxy_geo_with_ip", return_value=("America/New_York", "en-US", "1.2.3.4"))
    def test_geoip_with_string_proxy(self, mock_geo):
        tz, locale, ip = maybe_resolve_geoip(True, "http://proxy:8080", None, None)
        mock_geo.assert_called_once_with("http://proxy:8080")
        assert tz == "America/New_York"
        assert locale == "en-US"
        assert ip == "1.2.3.4"

    @patch("hexium_browser.geoip.resolve_proxy_geo_with_ip", return_value=("Europe/London", "en-GB", "5.6.7.8"))
    def test_geoip_with_dict_proxy_extracts_server(self, mock_geo):
        proxy_dict = {"server": "http://proxy:8080", "bypass": ".google.com"}
        tz, locale, ip = maybe_resolve_geoip(True, proxy_dict, None, None)
        mock_geo.assert_called_once_with("http://proxy:8080")
        assert tz == "Europe/London"
        assert locale == "en-GB"

    def test_geoip_disabled_skips_resolution(self):
        tz, locale, ip = maybe_resolve_geoip(False, "http://proxy:8080", None, None)
        assert tz is None
        assert locale is None
        assert ip is None

    @patch(
        "hexium_browser.geoip.resolve_proxy_geo_with_ip",
        return_value=("America/New_York", "en-US", "1.2.3.4"),
    )
    def test_geoip_no_proxy_uses_machine_ip(self, mock_geo):
        # No proxy → resolve the machine's own public IP (proxy_url=None).
        tz, locale, ip = maybe_resolve_geoip(True, None, None, None)
        mock_geo.assert_called_once_with(None)
        assert tz == "America/New_York"
        assert locale == "en-US"
        assert ip == "1.2.3.4"

    @patch("hexium_browser.geoip.resolve_proxy_geo_with_ip", return_value=("Asia/Tokyo", "ja-JP", "9.8.7.6"))
    def test_geoip_preserves_explicit_timezone(self, mock_geo):
        tz, locale, _ip = maybe_resolve_geoip(True, "http://proxy:8080", "Europe/Berlin", None)
        assert tz == "Europe/Berlin"
        assert locale == "ja-JP"

    @patch("hexium_browser.geoip.resolve_proxy_geo_with_ip", return_value=("America/New_York", "en-US", "1.2.3.4"))
    def test_geoip_normalizes_bare_proxy_with_creds(self, mock_geo):
        # "user:pass@host:port" must be normalized to http:// before geoip lookup.
        tz, locale, _ip = maybe_resolve_geoip(True, "user:pass@proxy:8080", None, None)
        mock_geo.assert_called_once_with("http://user:pass@proxy:8080")
        assert tz == "America/New_York"
        assert locale == "en-US"

    @patch("hexium_browser.geoip.resolve_proxy_geo_with_ip", return_value=("America/New_York", "en-US", "1.2.3.4"))
    def test_geoip_normalizes_schemeless_proxy_no_creds(self, mock_geo):
        # "host:port" (no @ and no scheme) must also be normalized.
        tz, locale, _ip = maybe_resolve_geoip(True, "proxy:8080", None, None)
        mock_geo.assert_called_once_with("http://proxy:8080")
        assert tz == "America/New_York"

    @patch("hexium_browser.geoip.resolve_proxy_geo_with_ip", return_value=("Europe/Berlin", "de-DE", "5.6.7.8"))
    def test_geoip_socks5_dict_reconstructs_credentials(self, mock_geo):
        proxy_dict = {"server": "socks5://proxy:1080", "username": "user", "password": "pass"}
        tz, locale, ip = maybe_resolve_geoip(True, proxy_dict, None, None)
        mock_geo.assert_called_once_with("socks5://user:pass@proxy:1080")
        assert tz == "Europe/Berlin"
        assert locale == "de-DE"

    @patch("hexium_browser.geoip.resolve_proxy_geo_with_ip", return_value=("Europe/Berlin", "de-DE", "5.6.7.8"))
    def test_geoip_socks5_dict_no_auth_uses_server(self, mock_geo):
        proxy_dict = {"server": "socks5://proxy:1080"}
        tz, locale, ip = maybe_resolve_geoip(True, proxy_dict, None, None)
        mock_geo.assert_called_once_with("socks5://proxy:1080")

    @patch("hexium_browser.geoip.resolve_proxy_geo_with_ip", return_value=("Europe/London", "en-GB", "1.1.1.1"))
    def test_geoip_http_dict_without_credentials_uses_server(self, mock_geo):
        proxy_dict = {"server": "http://proxy:8080"}
        tz, locale, ip = maybe_resolve_geoip(True, proxy_dict, None, None)
        mock_geo.assert_called_once_with("http://proxy:8080")

    @patch("hexium_browser.geoip.resolve_proxy_geo_with_ip", return_value=("Europe/London", "en-GB", "1.1.1.1"))
    def test_geoip_http_dict_reconstructs_credentials(self, mock_geo):
        proxy_dict = {"server": "http://proxy:8080", "username": "user", "password": "pass"}
        tz, locale, ip = maybe_resolve_geoip(True, proxy_dict, None, None)
        mock_geo.assert_called_once_with("http://user:pass@proxy:8080")


class TestBareProxyFormat:
    """_parse_proxy_url must handle bare 'user:pass@host:port' strings (no scheme)."""

    def test_bare_with_credentials(self):
        r = _parse_proxy_url("user:pass@proxy:8080")
        assert r["username"] == "user"
        assert r["password"] == "pass"
        assert r["server"] == "http://proxy:8080"

    def test_bare_credentials_not_in_server(self):
        r = _parse_proxy_url("user:pass@proxy1.example.com:5610")
        assert "user" not in r["server"]
        assert "pass" not in r["server"]

    def test_bare_username_only(self):
        r = _parse_proxy_url("user@proxy:8080")
        assert r["username"] == "user"
        assert "password" not in r
        assert r["server"] == "http://proxy:8080"

    def test_bare_no_port(self):
        r = _parse_proxy_url("user:pass@proxy.example.com")
        assert r["username"] == "user"
        assert r["password"] == "pass"
        assert r["server"] == "http://proxy.example.com"

    def test_bare_no_credentials_passthrough(self):
        # "host:port" without @ — no scheme, no creds — pass through unchanged
        r = _parse_proxy_url("proxy:8080")
        assert r == {"server": "proxy:8080"}

    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_resolve_proxy_config_bare(self, *_):
        kwargs, args = _resolve_proxy_config("user:pass@proxy:8080")
        _assert_proxy_network_args(args)
        assert kwargs == {
            "proxy": {"server": "http://proxy:8080", "username": "user", "password": "pass"}
        }


class TestIsSocksProxy:
    def test_socks5_string(self):
        assert _is_socks_proxy("socks5://user:pass@host:1080") is True

    def test_socks5h_string(self):
        assert _is_socks_proxy("socks5h://host:1080") is True

    def test_socks5_uppercase(self):
        assert _is_socks_proxy("SOCKS5://host:1080") is True

    def test_http_string(self):
        assert _is_socks_proxy("http://host:8080") is False

    def test_dict_socks5(self):
        assert _is_socks_proxy({"server": "socks5://host:1080"}) is True

    def test_dict_http(self):
        assert _is_socks_proxy({"server": "http://host:8080"}) is False

    def test_none(self):
        assert _is_socks_proxy(None) is False


class TestResolveProxyConfig:
    def test_none(self):
        kwargs, args = _resolve_proxy_config(None)
        assert kwargs == {}
        assert args == []

    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_http_string_with_creds_returns_playwright_dict(self, *_):
        kwargs, args = _resolve_proxy_config("http://user:pass@proxy:8080")
        assert kwargs == {
            "proxy": {"server": "http://proxy:8080", "username": "user", "password": "pass"}
        }
        _assert_proxy_network_args(args)

    def test_http_string_no_creds_returns_playwright_dict(self):
        kwargs, args = _resolve_proxy_config("http://proxy:8080")
        assert "proxy" in kwargs
        assert kwargs["proxy"]["server"] == "http://proxy:8080"
        _assert_proxy_network_args(args)

    def test_http_dict_passthrough(self):
        proxy = {"server": "http://proxy:8080", "bypass": ".example.com"}
        kwargs, args = _resolve_proxy_config(proxy)
        assert kwargs == {"proxy": proxy}
        _assert_proxy_network_args(args)

    def test_socks5_string_with_creds_uses_playwright_dict(self):
        kwargs, args = _resolve_proxy_config("socks5://user:pass@host:1080")
        assert kwargs == {
            "proxy": {
                "server": "socks5://host:1080",
                "username": "user",
                "password": "pass",
            }
        }
        _assert_proxy_network_args(args)

    def test_socks5_no_auth_returns_chrome_arg(self):
        kwargs, args = _resolve_proxy_config("socks5://host:1080")
        assert kwargs == {}
        assert args == ["--proxy-server=socks5://host:1080", *PROXY_NET]

    def test_socks5h_with_creds_uses_playwright_dict(self):
        kwargs, args = _resolve_proxy_config("socks5h://user:pass@host:1080")
        assert kwargs == {
            "proxy": {
                "server": "socks5h://host:1080",
                "username": "user",
                "password": "pass",
            }
        }
        _assert_proxy_network_args(args)

    def test_socks5_dict_with_creds_uses_playwright_dict(self):
        proxy = {"server": "socks5://host:1080", "username": "user", "password": "p@ss"}
        kwargs, args = _resolve_proxy_config(proxy)
        assert kwargs == {"proxy": proxy}
        _assert_proxy_network_args(args)

    def test_socks5_dict_ipv6_with_creds_uses_playwright_dict(self):
        proxy = {"server": "socks5://[::1]:1080", "username": "user", "password": "pass"}
        kwargs, args = _resolve_proxy_config(proxy)
        assert kwargs == {"proxy": proxy}
        _assert_proxy_network_args(args)

    def test_socks5_dict_with_bypass(self):
        proxy = {"server": "socks5://host:1080", "bypass": ".example.com"}
        kwargs, args = _resolve_proxy_config(proxy)
        assert kwargs == {}
        assert "--proxy-server=socks5://host:1080" in args
        assert "--proxy-bypass-list=.example.com" in args
        _assert_proxy_network_args(args)

    def test_socks5_string_with_creds_decodes_special_password(self):
        kwargs, _ = _resolve_proxy_config("socks5://user:pass=123@host:1080")
        assert kwargs["proxy"]["password"] == "pass=123"

    def test_socks5_string_with_creds_decodes_at_in_password(self):
        kwargs, _ = _resolve_proxy_config("socks5://user:p@ss@host:1080")
        assert kwargs["proxy"]["password"] == "p@ss"

    def test_socks5_string_with_creds_decodes_percent_encoded_password(self):
        kwargs, _ = _resolve_proxy_config("socks5://user:pass%3D123@host:1080")
        assert kwargs["proxy"]["password"] == "pass=123"

    def test_socks5_string_no_creds_unchanged(self):
        _, args = _resolve_proxy_config("socks5://host:1080")
        assert args == ["--proxy-server=socks5://host:1080", *PROXY_NET]

    def test_socks5_string_with_creds_empty_password(self):
        kwargs, args = _resolve_proxy_config("socks5://user:@host:1080")
        assert kwargs == {
            "proxy": {
                "server": "socks5://host:1080",
                "username": "user",
                "password": "",
            }
        }
        _assert_proxy_network_args(args)

    def test_socks5_string_with_creds_literal_percent_in_password(self):
        kwargs, _ = _resolve_proxy_config("socks5://user:100%sure@host:1080")
        assert kwargs["proxy"]["password"] == "100%sure"

    def test_socks5_string_with_creds_malformed_port(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="hexium_browser"):
            kwargs, args = _resolve_proxy_config("socks5://user:pass@host:abc")
        assert "proxy" in kwargs
        assert kwargs["proxy"]["username"] == "user"
        _assert_proxy_network_args(args)
        assert any("Malformed SOCKS5" in r.message for r in caplog.records)

    def test_socks5_string_with_creds_malformed_ipv6(self):
        kwargs, args = _resolve_proxy_config("socks5://user:pass@[::1")
        assert "proxy" in kwargs
        _assert_proxy_network_args(args)

    def test_socks5_string_with_creds_preserves_path_and_query(self):
        kwargs, _ = _resolve_proxy_config("socks5://user:pass@host:1080/p?x=1#f")
        assert kwargs["proxy"]["server"] == "socks5://host:1080/p?x=1#f"

    def test_socks5_string_with_creds_ipv6_special_password(self):
        kwargs, _ = _resolve_proxy_config("socks5://user:pass=eq@[::1]:1080")
        assert kwargs["proxy"]["password"] == "pass=eq"
        assert "[::1]" in kwargs["proxy"]["server"]

    def test_socks5_string_with_creds_port_zero(self):
        kwargs, _ = _resolve_proxy_config("socks5://user:pass=1@host:0")
        assert kwargs["proxy"]["server"] == "socks5://host:0"
        assert kwargs["proxy"]["password"] == "pass=1"

    # --- SOCKS5 with credentials → inline --proxy-server when opt-in ---

    @patch("hexium_browser.config._socks_proxy_inline_auth_enabled", return_value=True)
    @patch("hexium_browser.config.get_chromium_version", return_value="151.0.7922.174.1")
    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_socks5_string_inline_when_opt_in(self, *_):
        kwargs, args = _resolve_proxy_config("socks5://user:pass@host:1080")
        assert kwargs == {}
        assert args == ["--proxy-server=socks5://user:pass@host:1080", *PROXY_NET]

    @patch("hexium_browser.config._socks_proxy_inline_auth_enabled", return_value=True)
    @patch("hexium_browser.config.get_chromium_version", return_value="151.0.7922.174.1")
    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_socks5_dict_inline_when_opt_in(self, *_):
        proxy = {"server": "socks5://host:1080", "username": "user", "password": "p@ss"}
        kwargs, args = _resolve_proxy_config(proxy)
        assert kwargs == {}
        assert args[0].startswith("--proxy-server=socks5://user:p%40ss@host:1080")

    @patch("hexium_browser.config._socks_proxy_inline_auth_enabled", return_value=True)
    @patch("hexium_browser.config.get_chromium_version", return_value="151.0.7922.174.1")
    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_socks5_string_encodes_equals_inline_when_opt_in(self, *_):
        _, args = _resolve_proxy_config("socks5://user:pass=123@host:1080")
        assert args == ["--proxy-server=socks5://user:pass%3D123@host:1080", *PROXY_NET]

    @patch("hexium_browser.config._socks_proxy_inline_auth_enabled", return_value=True)
    @patch("hexium_browser.config.get_chromium_version", return_value="151.0.7922.174.1")
    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_socks5_string_logs_info_when_reencoding_inline(
        self, _tag, _ver, _enabled, caplog,
    ):
        import logging
        with caplog.at_level(logging.INFO, logger="hexium_browser"):
            _resolve_proxy_config("socks5://user:pass=123@host:1080")
        assert any("Auto URL-encoded SOCKS5" in r.message for r in caplog.records)

    @patch("hexium_browser.config._socks_proxy_inline_auth_enabled", return_value=True)
    @patch("hexium_browser.config.get_chromium_version", return_value="151.0.7922.174.1")
    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_socks5_string_malformed_port_inline(self, _tag, _ver, _enabled, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="hexium_browser"):
            _, args = _resolve_proxy_config("socks5://user:pass@host:abc")
        assert args == ["--proxy-server=socks5://user:pass@host:abc", *PROXY_NET]
        assert any("Malformed SOCKS5" in r.message for r in caplog.records)

    # --- HTTP with credentials → Playwright proxy dict (default until HX patch) ---

    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_http_string_with_creds_uses_playwright_dict(self, *_):
        kwargs, args = _resolve_proxy_config("http://user:pass@proxy:8080")
        assert kwargs == {
            "proxy": {"server": "http://proxy:8080", "username": "user", "password": "pass"}
        }
        _assert_proxy_network_args(args)

    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_http_dict_with_creds_uses_playwright_dict(self, *_):
        proxy = {"server": "http://proxy:8080", "username": "user", "password": "pass"}
        kwargs, args = _resolve_proxy_config(proxy)
        assert kwargs == {"proxy": proxy}
        _assert_proxy_network_args(args)

    @patch("hexium_browser.config._http_proxy_inline_auth_enabled", return_value=True)
    @patch("hexium_browser.config.get_chromium_version", return_value="151.0.7922.174.1")
    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_http_string_with_creds_inline_when_opt_in(self, *_):
        kwargs, args = _resolve_proxy_config("http://user:pass@proxy:8080")
        assert kwargs == {}
        assert args == ["--proxy-server=http://user:pass@proxy:8080", *PROXY_NET]

    @patch("hexium_browser.config._http_proxy_inline_auth_enabled", return_value=True)
    @patch("hexium_browser.config.get_chromium_version", return_value="151.0.7922.174.1")
    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_http_dict_with_creds_inline_when_opt_in(self, *_):
        proxy = {"server": "http://proxy:8080", "username": "user", "password": "pass"}
        kwargs, args = _resolve_proxy_config(proxy)
        assert kwargs == {}
        assert args == ["--proxy-server=http://user:pass@proxy:8080", *PROXY_NET]

    @patch("hexium_browser.config._http_proxy_inline_auth_enabled", return_value=True)
    @patch("hexium_browser.config.get_chromium_version", return_value="151.0.7922.174.1")
    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_http_dict_with_creds_and_bypass_inline_when_opt_in(self, *_):
        proxy = {
            "server": "http://proxy:8080",
            "username": "user",
            "password": "pass",
            "bypass": ".google.com",
        }
        kwargs, args = _resolve_proxy_config(proxy)
        assert kwargs == {}
        assert "--proxy-server=http://user:pass@proxy:8080" in args
        assert "--proxy-bypass-list=.google.com" in args
        _assert_proxy_network_args(args)

    @patch("hexium_browser.config._http_proxy_inline_auth_enabled", return_value=True)
    @patch("hexium_browser.config.get_chromium_version", return_value="151.0.7922.174.1")
    @patch("hexium_browser.config.get_platform_tag", return_value="linux-x64")
    def test_http_string_encodes_special_chars_inline_when_opt_in(self, *_):
        _, args = _resolve_proxy_config("http://user:pass=123@proxy:8080")
        assert args == ["--proxy-server=http://user:pass%3D123@proxy:8080", *PROXY_NET]

    @patch("hexium_browser.config.get_platform_tag", return_value="darwin-arm64")
    def test_http_string_with_creds_on_macos_falls_back(self, _mock):
        kwargs, args = _resolve_proxy_config(
            "http://user:pass@proxy:8080", browser_version="146.0.7680.177.3"
        )
        assert "proxy" in kwargs
        assert kwargs["proxy"]["username"] == "user"
        _assert_proxy_network_args(args)

    @patch("hexium_browser.config.get_platform_tag", return_value="darwin-arm64")
    def test_http_dict_with_creds_on_macos_falls_back(self, _mock):
        proxy = {"server": "http://proxy:8080", "username": "user", "password": "pass"}
        kwargs, args = _resolve_proxy_config(proxy, browser_version="146.0.7680.177.3")
        assert kwargs == {"proxy": proxy}
        _assert_proxy_network_args(args)

    @patch("hexium_browser.config.get_platform_tag", return_value="linux-arm64")
    def test_http_string_with_creds_on_linux_arm_falls_back(self, _mock):
        kwargs, args = _resolve_proxy_config(
            "http://user:pass@proxy:8080", browser_version="146.0.7680.177.3"
        )
        assert "proxy" in kwargs
        _assert_proxy_network_args(args)

    @patch("hexium_browser.config._http_proxy_inline_auth_enabled", return_value=True)
    @patch("hexium_browser.config.get_platform_tag", return_value="darwin-arm64")
    def test_http_with_creds_inline_when_opt_in(self, _tag, _enabled):
        kwargs, args = _resolve_proxy_config(
            "http://user:pass@proxy:8080", browser_version="151.0.7922.174.1"
        )
        assert kwargs == {}
        assert args == ["--proxy-server=http://user:pass@proxy:8080", *PROXY_NET]

    # --- HTTP without credentials (all platforms) ---

    def test_http_no_creds_returns_playwright_dict(self):
        kwargs, args = _resolve_proxy_config("http://proxy:8080")
        assert "proxy" in kwargs
        _assert_proxy_network_args(args)

    def test_http_dict_no_creds_returns_playwright_dict(self):
        proxy = {"server": "http://proxy:8080", "bypass": ".example.com"}
        kwargs, args = _resolve_proxy_config(proxy)
        assert kwargs == {"proxy": proxy}
        _assert_proxy_network_args(args)


class TestWebrtcMaskEnv:
    def test_from_args_ignores_auto(self):
        from hexium_browser.browser import webrtc_mask_ip_from_args

        assert webrtc_mask_ip_from_args(["--hexium-webrtc-ip=auto"]) is None
        assert webrtc_mask_ip_from_args(["--hexium-webrtc-ip=87.192.108.115"]) == (
            "87.192.108.115"
        )

    def test_ensure_sets_env_and_kwargs(self, monkeypatch):
        import os

        from hexium_browser.browser import WEBRTC_MASK_ENV, _ensure_webrtc_mask_env

        monkeypatch.delenv(WEBRTC_MASK_ENV, raising=False)
        kwargs: dict = {}
        _ensure_webrtc_mask_env(kwargs, ["--hexium-webrtc-ip=87.192.108.115"])
        assert kwargs["env"][WEBRTC_MASK_ENV] == "87.192.108.115"
        assert os.environ[WEBRTC_MASK_ENV] == "87.192.108.115"
