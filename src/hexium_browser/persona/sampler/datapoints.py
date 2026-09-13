"""Paths to Hexium-vendored device-network definition files."""

from __future__ import annotations

from pathlib import Path

_DATA = Path(__file__).resolve().parent.parent / "data"


def get_browser_helper_file() -> Path:
    return _DATA / "browser-helper-file.json"


def get_header_network() -> Path:
    return _DATA / "header-network-definition.zip"


def get_headers_order() -> Path:
    return _DATA / "headers-order.json"


def get_input_network() -> Path:
    return _DATA / "input-network-definition.zip"


def get_fingerprint_network() -> Path:
    return _DATA / "fingerprint-network-definition.zip"
