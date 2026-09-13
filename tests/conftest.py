"""Shared pytest fixtures."""

import pytest


@pytest.fixture(autouse=True)
def isolated_cache_dir(tmp_path_factory, monkeypatch):
    """Keep the suite away from the developer's real ``~/.hexium`` cache."""
    monkeypatch.setenv(
        "HEXIUM_CACHE_DIR",
        str(tmp_path_factory.mktemp("hexium-cache")),
    )


@pytest.fixture(autouse=True)
def stub_geoip_lookup(request, monkeypatch):
    """Keep unit tests off echo services / GeoLite2 after geoip defaults True.

    ``test_geoip.py`` and ``test_proxy.py`` patch the helper themselves.
    ``exit_ip=None`` avoids stuffing ``--hexium-webrtc-ip=`` with a fake IP.
    """
    path = str(getattr(request.node, "path", "") or "")
    if "test_geoip.py" in path or "test_proxy.py" in path:
        return

    monkeypatch.setattr(
        "hexium_browser.geoip.resolve_proxy_geo_with_ip",
        lambda *_a, **_k: ("America/New_York", "en-US", None),
    )


@pytest.fixture(autouse=True)
def stub_linux_chrome_sample(request, monkeypatch):
    """Avoid BrowserForge draws in unrelated launch tests.

    Persona unit tests exercise sampling themselves (and mock ``_draw_linux_chrome``).
    """
    path = str(getattr(request.node, "path", "") or "")
    if "test_persona" in path:
        return

    def _stub(seed: str):
        from hexium_browser.persona.coerce import coerce_fingerprint
        from hexium_browser.persona.rewrite_ua import rewrite_chrome_version
        from hexium_browser.persona.schema import CHROME_UA_VERSION
        from tests.persona_fixtures import linux_chrome_149_fingerprint

        return rewrite_chrome_version(
            coerce_fingerprint(linux_chrome_149_fingerprint(), seed=seed),
            CHROME_UA_VERSION,
        )

    monkeypatch.setattr("hexium_browser.browser.sample_linux_chrome", _stub)
