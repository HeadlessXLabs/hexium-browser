"""Unit tests for Widevine CDM hint-file seeding (src/hexium_browser/widevine.py)."""

import json

import pytest

from hexium_browser import widevine
from hexium_browser.widevine import resolve_widevine_cdm_dir, seed_widevine_hint

_HINT = "WidevineCdm/latest-component-updated-widevine-cdm"


@pytest.fixture(autouse=True)
def _force_linux(monkeypatch, tmp_path):
    """Run as if on Linux unless a test overrides it (seeding is Linux-only)."""
    monkeypatch.setattr(widevine.platform, "system", lambda: "Linux")
    monkeypatch.delenv("HEXIUM_WIDEVINE", raising=False)
    monkeypatch.delenv("HEXIUM_WIDEVINE_CDM", raising=False)
    # Isolate the cache-root fallback from any real ~/.hexium_browser on the host.
    monkeypatch.setenv("HEXIUM_CACHE_DIR", str(tmp_path / "_isolated_cache"))


def _make_cdm(dirpath):
    """Create a fake WidevineCdm dir with a manifest.json."""
    dirpath.mkdir(parents=True, exist_ok=True)
    (dirpath / "manifest.json").write_text('{"version": "4.10.3050.0"}')
    return dirpath


def _binary(tmp_path):
    """Return a fake chrome binary path inside its own dir."""
    bdir = tmp_path / "bin"
    bdir.mkdir(parents=True, exist_ok=True)
    return bdir / "chrome"


def test_seeds_hint_next_to_binary(tmp_path):
    """CDM in <binary dir>/WidevineCdm -> hint file written with abs Path."""
    binary = _binary(tmp_path)
    cdm = _make_cdm(binary.parent / "WidevineCdm")

    profile = tmp_path / "profile"
    seed_widevine_hint(profile, binary)

    hint = profile / _HINT
    assert hint.is_file()
    assert json.loads(hint.read_text())["Path"] == str(cdm.resolve())


def test_seeds_hint_from_env_var(tmp_path, monkeypatch):
    """HEXIUM_WIDEVINE_CDM takes priority and is used as the Path."""
    cdm = _make_cdm(tmp_path / "custom_cdm")
    monkeypatch.setenv("HEXIUM_WIDEVINE_CDM", str(cdm))

    profile = tmp_path / "profile"
    seed_widevine_hint(profile, _binary(tmp_path))

    assert json.loads((profile / _HINT).read_text())["Path"] == str(cdm.resolve())


def test_no_cdm_no_file(tmp_path):
    """No CDM present -> nothing written, no exception."""
    profile = tmp_path / "profile"
    seed_widevine_hint(profile, _binary(tmp_path))
    assert not (profile / _HINT).exists()


def test_kill_switch_disables(tmp_path, monkeypatch):
    """HEXIUM_WIDEVINE=0 disables seeding even when a CDM exists."""
    monkeypatch.setenv("HEXIUM_WIDEVINE_CDM", str(_make_cdm(tmp_path / "custom_cdm")))
    monkeypatch.setenv("HEXIUM_WIDEVINE", "0")

    profile = tmp_path / "profile"
    seed_widevine_hint(profile, _binary(tmp_path))
    assert not (profile / _HINT).exists()


def test_idempotent(tmp_path, monkeypatch):
    """Seeding twice leaves the same correct content and doesn't error."""
    cdm = _make_cdm(tmp_path / "custom_cdm")
    monkeypatch.setenv("HEXIUM_WIDEVINE_CDM", str(cdm))

    profile = tmp_path / "profile"
    binary = _binary(tmp_path)
    seed_widevine_hint(profile, binary)
    seed_widevine_hint(profile, binary)
    assert json.loads((profile / _HINT).read_text())["Path"] == str(cdm.resolve())


def test_noop_on_non_linux(tmp_path, monkeypatch):
    """On non-Linux, seeding is a no-op even with a CDM present."""
    monkeypatch.setattr(widevine.platform, "system", lambda: "Windows")
    monkeypatch.setenv("HEXIUM_WIDEVINE_CDM", str(_make_cdm(tmp_path / "cdm")))

    profile = tmp_path / "profile"
    seed_widevine_hint(profile, _binary(tmp_path))
    assert not (profile / _HINT).exists()


def test_resolve_requires_manifest(tmp_path, monkeypatch):
    """A WidevineCdm dir without manifest.json is not treated as a CDM."""
    bogus = tmp_path / "custom_cdm"
    bogus.mkdir()
    monkeypatch.setenv("HEXIUM_WIDEVINE_CDM", str(bogus))
    assert resolve_widevine_cdm_dir(_binary(tmp_path)) is None


def test_env_var_is_exclusive(tmp_path, monkeypatch):
    """An invalid HEXIUM_WIDEVINE_CDM skips seeding — no fallback to binary dir."""
    binary = _binary(tmp_path)
    _make_cdm(binary.parent / "WidevineCdm")  # valid CDM next to binary
    bogus = tmp_path / "bogus"
    bogus.mkdir()  # set but no manifest.json
    monkeypatch.setenv("HEXIUM_WIDEVINE_CDM", str(bogus))
    assert resolve_widevine_cdm_dir(binary) is None


def test_resolve_falls_back_to_cache_root(tmp_path, monkeypatch):
    """No CDM next to the binary -> auto-detect falls back to <cache>/WidevineCdm.

    Simulates the Pro case: a Pro binary sits in its own chromium-<ver>-pro dir
    with no adjacent CDM, while the Docker auto-fetch left one at the cache root.
    """
    cache = tmp_path / "cache"
    monkeypatch.setenv("HEXIUM_CACHE_DIR", str(cache))
    cdm = _make_cdm(cache / "WidevineCdm")
    pro_binary = tmp_path / "chromium-148.0-pro" / "chrome"
    pro_binary.parent.mkdir(parents=True)  # binary dir exists, but has no CDM
    assert resolve_widevine_cdm_dir(pro_binary) == cdm.resolve()


def test_resolve_binary_dir_wins_over_cache_root(tmp_path, monkeypatch):
    """A manual sideload next to the binary takes precedence over the cache root."""
    cache = tmp_path / "cache"
    monkeypatch.setenv("HEXIUM_CACHE_DIR", str(cache))
    _make_cdm(cache / "WidevineCdm")  # cache-root CDM present...
    binary = _binary(tmp_path)
    next_to = _make_cdm(binary.parent / "WidevineCdm")  # ...but sideload wins
    assert resolve_widevine_cdm_dir(binary) == next_to.resolve()


def test_seeds_hint_from_cache_root_fallback(tmp_path, monkeypatch):
    """End-to-end: a cache-root CDM seeds the hint for a binary with none adjacent."""
    cache = tmp_path / "cache"
    monkeypatch.setenv("HEXIUM_CACHE_DIR", str(cache))
    cdm = _make_cdm(cache / "WidevineCdm")
    profile = tmp_path / "profile"
    seed_widevine_hint(profile, _binary(tmp_path))  # binary has no adjacent CDM
    assert json.loads((profile / _HINT).read_text())["Path"] == str(cdm.resolve())


def test_empty_env_var_is_exclusive(tmp_path, monkeypatch):
    """An empty (but set) HEXIUM_WIDEVINE_CDM resolves to None — and must NOT
    pick up a stray manifest.json in the working directory (``Path("")`` -> ``.``)."""
    binary = _binary(tmp_path)
    _make_cdm(binary.parent / "WidevineCdm")  # valid CDM next to binary
    monkeypatch.setenv("HEXIUM_WIDEVINE_CDM", "")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / "manifest.json").write_text("{}")  # stray manifest in CWD must be ignored
    monkeypatch.chdir(cwd)
    assert resolve_widevine_cdm_dir(binary) is None


def test_empty_user_data_dir_skips(tmp_path, monkeypatch):
    """Empty user_data_dir (ephemeral profile) -> no CWD pollution, no seeding."""
    cdm = _make_cdm(tmp_path / "custom_cdm")
    monkeypatch.setenv("HEXIUM_WIDEVINE_CDM", str(cdm))
    monkeypatch.chdir(tmp_path)
    seed_widevine_hint("", _binary(tmp_path))
    assert not (tmp_path / "WidevineCdm").exists()


def test_never_raises_on_write_failure(tmp_path, monkeypatch):
    """A write failure (hint dir path is a file) must not raise — launch must not break."""
    cdm = _make_cdm(tmp_path / "custom_cdm")
    monkeypatch.setenv("HEXIUM_WIDEVINE_CDM", str(cdm))
    profile = tmp_path / "profile"
    profile.mkdir()
    # Block mkdir of <profile>/WidevineCdm by occupying that path with a file.
    (profile / "WidevineCdm").write_text("not a dir")

    seed_widevine_hint(profile, _binary(tmp_path))  # must not raise


def test_rewrites_corrupt_existing_hint(tmp_path, monkeypatch):
    """A non-UTF8 / mismatched existing hint is overwritten, without raising."""
    cdm = _make_cdm(tmp_path / "custom_cdm")
    monkeypatch.setenv("HEXIUM_WIDEVINE_CDM", str(cdm))
    profile = tmp_path / "profile"
    hint = profile / "WidevineCdm" / _HINT.split("/")[-1]
    hint.parent.mkdir(parents=True)
    hint.write_bytes(b"\xff\xfe not valid utf-8")

    seed_widevine_hint(profile, _binary(tmp_path))  # must not raise

    # corrupt content replaced with a valid hint pointing at the CDM
    assert json.loads(hint.read_text())["Path"] == str(cdm.resolve())
