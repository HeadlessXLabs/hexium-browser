"""Unit tests for persona datapack Chrome cloning (tiny fixtures only)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from hexium_browser.persona.datapack import (
    clone_probability_tree,
    extend_possible_values,
    is_mobile_ua,
    rewrite_chrome_token,
    rewrite_chrome_tokens,
    upgrade_datapack_dir,
    upgrade_helper_lines,
    upgrade_network_definition,
)


def test_skip_mobile():
    assert is_mobile_ua(
        "Mozilla/5.0 (Linux; Android 10; K) Chrome/144.0.0.0 Mobile Safari/537.36"
    )
    assert not is_mobile_ua(
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/144.0.0.0 Safari/537.36"
    )


def test_rewrite_header_browser_to_151_exact_builds():
    out = rewrite_chrome_tokens("chrome/144.0.0.0", 151)
    assert "chrome/151.0.7922.173" in out  # linux
    assert "chrome/151.0.7922.176" in out  # windows/macos
    assert "chrome/151.0.0.0" not in out


def test_rewrite_header_browser_to_148_exact_builds():
    out = rewrite_chrome_tokens("chrome/144.0.0.0", 148)
    assert "chrome/148.0.7778.215" in out
    assert "chrome/148.0.7778.218" in out
    assert "chrome/148.0.7778.217" in out


def test_rewrite_windows_ua_144_to_148():
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/144.0.7559.95 Safari/537.36"
    )
    out = rewrite_chrome_token(ua, 148)
    assert out is not None
    assert "Chrome/148.0.7778.218" in out
    assert "Chrome/144" not in out
    assert "Chrome/148.0.0.0" not in out


def test_rewrite_linux_ua_147_to_153_not_missing_154():
    ua = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    )
    assert rewrite_chrome_tokens(ua, 154) == []
    out = rewrite_chrome_token(ua, 153)
    assert out is not None
    assert "Chrome/153.0.8010.36" in out


def test_rewrite_windows_ua_to_154():
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    )
    out = rewrite_chrome_token(ua, 154)
    assert out is not None
    assert "Chrome/154.0.8037.17" in out


def test_rewrite_ignores_safari():
    assert rewrite_chrome_token("safari/26.2", 151) is None


def test_rewrite_ignores_non_source_major():
    assert rewrite_chrome_token("chrome/139.0.0.0", 148) is None


def test_clone_tree_adds_exact_keys_keeps_old():
    tree = {"chrome/144.0.0.0": {"p": 1.0}, "safari/26.2": {"p": 1.0}}
    cloned = clone_probability_tree(tree)
    assert "chrome/144.0.0.0" in cloned
    assert cloned["chrome/151.0.7922.173"] == {"p": 1.0}
    assert "chrome/148.0.7778.215" in cloned
    assert "chrome/154.0.8037.17" in cloned
    assert "safari/26.2" in cloned


def test_extend_possible_values_desktop_only():
    values = [
        "chrome/144.0.0.0",
        "Mozilla/5.0 (Linux; Android 10; K) Chrome/144.0.0.0 Mobile Safari/537.36",
        "safari/26.2",
    ]
    out = extend_possible_values(values)
    assert "chrome/144.0.0.0" in out
    assert "chrome/148.0.7778.215" in out
    assert "chrome/151.0.7922.173" in out
    assert "chrome/154.0.8037.17" in out
    assert sum("Mobile" in v for v in out) == 1


def test_upgrade_network_definition_clones_cpt_and_values():
    net = {
        "nodes": [
            {
                "name": "*BROWSER",
                "possibleValues": ["chrome/144.0.0.0", "safari/26.2"],
                "conditionalProbabilities": {"chrome/144.0.0.0": 0.9, "safari/26.2": 0.1},
            }
        ]
    }
    upgraded = upgrade_network_definition(net)
    node = upgraded["nodes"][0]
    assert "chrome/151.0.7922.173" in node["possibleValues"]
    assert "chrome/154.0.8037.17" in node["possibleValues"]
    assert node["conditionalProbabilities"]["chrome/151.0.7922.173"] == 0.9


def test_upgrade_helper_lines():
    lines = ["chrome/144.0.0.0|2", "safari/26.2|2"]
    out = upgrade_helper_lines(lines)
    assert "chrome/144.0.0.0|2" in out
    assert "chrome/151.0.7922.173|2" in out
    assert "chrome/154.0.8037.17|2" in out
    assert "safari/26.2|2" in out


def test_upgrade_datapack_dir_roundtrip(tmp_path: Path):
    unpacked_h = tmp_path / "unpacked" / "header-network-definition"
    unpacked_h.mkdir(parents=True)
    net = {
        "nodes": [
            {
                "name": "*BROWSER",
                "possibleValues": ["chrome/147.0.0.0"],
                "conditionalProbabilities": {"chrome/147.0.0.0": 1.0},
            }
        ]
    }
    (unpacked_h / "network.json").write_text(json.dumps(net))

    unpacked_f = tmp_path / "unpacked" / "fingerprint-network-definition"
    unpacked_f.mkdir(parents=True)
    ua = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    )
    fp = {
        "nodes": [
            {
                "name": "userAgent",
                "possibleValues": [ua],
                "conditionalProbabilities": {ua: 1.0},
            }
        ]
    }
    (unpacked_f / "network.json").write_text(json.dumps(fp))
    (tmp_path / "browser-helper-file.json").write_text(json.dumps(["chrome/147.0.0.0|2"]))
    (tmp_path / "unpacked" / "input-network-definition").mkdir()
    (tmp_path / "unpacked" / "input-network-definition" / "network.json").write_text(
        json.dumps({"nodes": []})
    )

    upgrade_datapack_dir(tmp_path)

    helper = json.loads((tmp_path / "browser-helper-file.json").read_text())
    assert any("chrome/151.0.7922.173" in line for line in helper)
    assert any("chrome/154.0.8037.17" in line for line in helper)
    with zipfile.ZipFile(tmp_path / "header-network-definition.zip") as z:
        upgraded = json.loads(z.read("network.json"))
    assert "chrome/151.0.7922.173" in upgraded["nodes"][0]["possibleValues"]
    assert "chrome/154.0.8037.17" in upgraded["nodes"][0]["possibleValues"]
    with zipfile.ZipFile(tmp_path / "fingerprint-network-definition.zip") as z:
        fp_up = json.loads(z.read("network.json"))
    uas = fp_up["nodes"][0]["possibleValues"]
    assert any("Chrome/153.0.8010.36" in u for u in uas)
    assert not any("Chrome/154." in u for u in uas)
