import sys
from argparse import Namespace

import pytest

from hexium_browser.__main__ import cmd_profiles, main


def test_list_empty(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_PROFILES_DIR", raising=False)
    cmd_profiles(Namespace(profiles_cmd="list", name=None))
    assert capsys.readouterr().out.strip() == ""


def test_new_use_list_last(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_PROFILES_DIR", raising=False)
    cmd_profiles(Namespace(profiles_cmd="new", name="Work"))
    created = capsys.readouterr().out.strip()
    assert created.endswith("profiles/Work")
    cmd_profiles(Namespace(profiles_cmd="use", name="Work"))
    cmd_profiles(Namespace(profiles_cmd="list", name=None))
    listed = capsys.readouterr().out
    assert "Work (last)" in listed
    cmd_profiles(Namespace(profiles_cmd="last", name=None))
    assert capsys.readouterr().out.strip().endswith("profiles/Work")


def test_use_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="Work"):
        cmd_profiles(Namespace(profiles_cmd="use", name="Work"))


def test_new_requires_name(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    with pytest.raises(ValueError, match="name"):
        cmd_profiles(Namespace(profiles_cmd="new", name=None))


def test_main_profiles_list_exit_zero(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["hexium-browser", "profiles", "list"])
    main()


def test_main_profiles_bare_lists(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    monkeypatch.delenv("HEXIUM_PROFILES_DIR", raising=False)
    monkeypatch.setattr(sys, "argv", ["hexium-browser", "profiles"])
    main()
    assert capsys.readouterr().out.strip() == ""


def test_last_unset_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXIUM_HOME", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="no last named profile"):
        cmd_profiles(Namespace(profiles_cmd="last", name=None))
