"""UA and UA-CH must be rewritten to Chrome 151 together."""

from __future__ import annotations

from tests.persona_fixtures import linux_chrome_149_fingerprint, windows_chrome_147_fingerprint

from hexium_browser.persona.coerce import coerce_fingerprint
from hexium_browser.persona.rewrite_ua import (
    clamp_windows_ua_ch_platform_version,
    rewrite_chrome_version,
    sync_windows_frozen_ua_platform_version,
)
from hexium_browser.persona.schema import CHROME_UA_VERSION


def test_rewrite_updates_ua_and_uach_together():
    persona = coerce_fingerprint(linux_chrome_149_fingerprint(), seed="seed-1")
    rewritten = rewrite_chrome_version(persona, CHROME_UA_VERSION)

    assert f"Chrome/{CHROME_UA_VERSION}" in rewritten["user_agent"]
    assert "Chrome/149" not in rewritten["user_agent"]
    assert rewritten["ua_ch_full_version"] == CHROME_UA_VERSION

    chrome_versions = [
        item["version"]
        for item in rewritten["ua_ch_full_version_list"]
        if item["brand"] in ("Google Chrome", "Chromium")
    ]
    assert chrome_versions
    assert all(version == CHROME_UA_VERSION for version in chrome_versions)


def test_rewrite_does_not_leave_149_uach_with_151_ua():
    persona = coerce_fingerprint(linux_chrome_149_fingerprint(), seed="seed-1")
    rewritten = rewrite_chrome_version(persona, CHROME_UA_VERSION)

    assert "151.0.7922.174" in rewritten["user_agent"]
    assert rewritten["ua_ch_full_version"] != "149.0.7672.114"
    for item in rewritten["ua_ch_full_version_list"]:
        if item["brand"] in ("Google Chrome", "Chromium"):
            assert "149" not in item["version"]


def test_rewrite_leaves_grease_brand_alone():
    persona = coerce_fingerprint(linux_chrome_149_fingerprint(), seed="seed-1")
    rewritten = rewrite_chrome_version(persona, CHROME_UA_VERSION)
    grease = [
        item for item in rewritten["ua_ch_full_version_list"] if "Brand" in item["brand"]
    ]
    assert grease
    assert all(item["version"] != CHROME_UA_VERSION for item in grease)


def test_rewrite_leaves_windows_platform_version_alone():
    persona = coerce_fingerprint(windows_chrome_147_fingerprint(), seed="seed-1")
    assert persona["ua_ch_platform_version"] == "10.0.0"
    rewritten = rewrite_chrome_version(persona, CHROME_UA_VERSION)
    assert rewritten["ua_ch_platform_version"] == "10.0.0"
    assert f"Chrome/{CHROME_UA_VERSION}" in rewritten["user_agent"]
    assert rewritten["ua_ch_full_version"] == CHROME_UA_VERSION
    chrome_versions = [
        item["version"]
        for item in rewritten["ua_ch_full_version_list"]
        if item["brand"] in ("Google Chrome", "Chromium")
    ]
    assert chrome_versions
    assert all(version == CHROME_UA_VERSION for version in chrome_versions)

    win10 = coerce_fingerprint(
        windows_chrome_147_fingerprint(
            navigator={"userAgentData": {"platformVersion": "10.0.0"}}
        ),
        seed="seed-1",
    )
    rewritten10 = rewrite_chrome_version(win10, CHROME_UA_VERSION)
    assert rewritten10["ua_ch_platform_version"] == "10.0.0"


def test_clamp_windows_ua_ch_platform_version():
    assert clamp_windows_ua_ch_platform_version("19.0.0") == "15.0.0"
    assert clamp_windows_ua_ch_platform_version("13.0.0") == "15.0.0"
    assert clamp_windows_ua_ch_platform_version("10.0.0") == "10.0.0"
    assert clamp_windows_ua_ch_platform_version("6.8.0") == "15.0.0"
    assert clamp_windows_ua_ch_platform_version("") == "15.0.0"
    assert clamp_windows_ua_ch_platform_version("not-a-version") == "15.0.0"


def test_sync_windows_frozen_ua_platform_version():
    persona = coerce_fingerprint(windows_chrome_147_fingerprint(), seed="seed-1")
    assert persona["ua_ch_platform_version"] == "10.0.0"
    persona["ua_ch_platform_version"] = "15.0.0"
    sync_windows_frozen_ua_platform_version(persona)
    assert persona["ua_ch_platform_version"] == "10.0.0"


def test_windows_coerce_clamps_contract_and_kernel_platform_version():
    contract19 = coerce_fingerprint(
        windows_chrome_147_fingerprint(
            navigator={"userAgentData": {"platformVersion": "19.0.0"}}
        ),
        seed="seed-1",
    )
    assert contract19["ua_ch_platform_version"] == "10.0.0"

    contract13 = coerce_fingerprint(
        windows_chrome_147_fingerprint(
            navigator={"userAgentData": {"platformVersion": "13.0.0"}}
        ),
        seed="seed-1",
    )
    assert contract13["ua_ch_platform_version"] == "10.0.0"

    kernel = coerce_fingerprint(
        windows_chrome_147_fingerprint(
            navigator={"userAgentData": {"platformVersion": "6.8.0"}}
        ),
        seed="seed-1",
    )
    assert kernel["ua_ch_platform_version"] == "10.0.0"
