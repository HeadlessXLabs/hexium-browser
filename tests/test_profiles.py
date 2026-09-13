from pathlib import Path

import pytest

from hexium_browser.profiles import (
    DEFAULT_PROFILE_NAME,
    assert_persistent_profile,
    ensure_profile,
    get_hexium_home,
    get_last_profile_name,
    get_profiles_root,
    list_profile_names,
    resolve_launch_user_data_dir,
    set_last_profile_name,
)


def test_home_default(monkeypatch, tmp_path):
    monkeypatch.delenv("HEXIUM_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert get_hexium_home() == tmp_path / ".hexium"


def test_home_override(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path / "hx"))
    assert get_hexium_home() == tmp_path / "hx"


def test_profiles_root_under_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_PROFILES_DIR", raising=False)
    assert get_profiles_root() == tmp_path / "profiles"


def test_profiles_root_env_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path / "hx"))
    monkeypatch.setenv("HEXIUM_PROFILES_DIR", str(tmp_path / "lab"))
    assert get_profiles_root() == tmp_path / "lab"


def test_does_not_auto_use_drive512(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_PROFILES_DIR", raising=False)
    assert "Drive512" not in str(get_profiles_root())


def test_ensure_and_list(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_PROFILES_DIR", raising=False)
    ensure_profile("Work")
    names = list_profile_names()
    assert "Work" in names
    assert DEFAULT_PROFILE_NAME not in names  # not created until ensure/resolve


def test_last_profile_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_PROFILES_DIR", raising=False)
    ensure_profile("Work")
    set_last_profile_name("Work")
    assert get_last_profile_name() == "Work"


def test_resolve_bare_launch_is_new_session_each_time(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    monkeypatch.delenv("HEXIUM_PROFILES_DIR", raising=False)
    a = resolve_launch_user_data_dir()
    b = resolve_launch_user_data_dir()
    assert a != b
    assert a.parent == tmp_path / "profiles"
    assert a.name.startswith("hexium-session-")
    assert b.name.startswith("hexium-session-")
    assert a.is_dir() and b.is_dir()


def test_resolve_named_profile(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    path = resolve_launch_user_data_dir(profile="Work")
    assert path == tmp_path / "profiles" / "Work"
    assert get_last_profile_name() == "Work"


def test_explicit_path_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    custom = tmp_path / "custom-ud"
    path = resolve_launch_user_data_dir(custom)
    assert path == custom.resolve()
    assert custom.is_dir()


def test_env_pin_wins_over_default(monkeypatch, tmp_path):
    pinned = tmp_path / "pinned"
    monkeypatch.setenv("HEXIUM_USER_DATA_DIR", str(pinned))
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path / "hx"))
    path = resolve_launch_user_data_dir()
    assert path == pinned.resolve()


def test_last_profile_ignored_on_bare_resolve(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    ensure_profile("Work")
    set_last_profile_name("Work")
    path = resolve_launch_user_data_dir()
    assert path != tmp_path / "profiles" / "Work"
    assert path.name.startswith("hexium-session-")


def test_invalid_profile_name_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    with pytest.raises(ValueError, match="profile name"):
        resolve_launch_user_data_dir(profile="../etc")
    with pytest.raises(ValueError, match="profile name"):
        resolve_launch_user_data_dir(profile="foo/bar")


def test_refuse_tmp(tmp_path):
    with pytest.raises(RuntimeError, match="tmpfs|Incognito|/tmp"):
        assert_persistent_profile(Path("/tmp/hexium-evil"))


def test_ephemeral_under_profiles_root(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_USER_DATA_DIR", raising=False)
    path = resolve_launch_user_data_dir(ephemeral=True)
    assert path.parent == tmp_path / "profiles"
    assert path.name.startswith("hexium-session-")
    other = resolve_launch_user_data_dir(ephemeral=True)
    assert other != path
