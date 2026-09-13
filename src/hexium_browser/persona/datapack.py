"""Clone desktop Chrome CPT/UA keys using exact Stable four-part versions."""

from __future__ import annotations

import copy
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Literal

# Latest Stable four-part builds from ChromiumDash (channel=Stable), Sep 2026.
# Linux Stable has no 154 yet; Windows/macOS do.
CHROME_STABLE: dict[str, dict[int, str]] = {
    "linux": {
        140: "140.0.7339.207",
        141: "141.0.7390.122",
        142: "142.0.7444.175",
        143: "143.0.7499.192",
        144: "144.0.7559.132",
        145: "145.0.7632.159",
        146: "146.0.7680.177",
        147: "147.0.7727.137",
        148: "148.0.7778.215",
        149: "149.0.7827.200",
        150: "150.0.7871.186",
        151: "151.0.7922.173",
        152: "152.0.7977.82",
        153: "153.0.8010.36",
    },
    "windows": {
        140: "140.0.7339.210",
        141: "141.0.7390.125",
        142: "142.0.7444.177",
        143: "143.0.7499.194",
        144: "144.0.7559.135",
        145: "145.0.7632.162",
        146: "146.0.7680.180",
        147: "147.0.7727.139",
        148: "148.0.7778.218",
        149: "149.0.7827.201",
        150: "150.0.7871.189",
        151: "151.0.7922.176",
        152: "152.0.7977.85",
        153: "153.0.8010.37",
        154: "154.0.8037.17",
    },
    "macos": {
        140: "140.0.7339.215",
        141: "141.0.7390.124",
        142: "142.0.7444.177",
        143: "143.0.7499.194",
        144: "144.0.7559.135",
        145: "145.0.7632.162",
        146: "146.0.7680.180",
        147: "147.0.7727.139",
        148: "148.0.7778.217",
        149: "149.0.7827.201",
        150: "150.0.7871.189",
        151: "151.0.7922.176",
        152: "152.0.7977.85",
        153: "153.0.8010.37",
        154: "154.0.8037.17",
    },
}

SOURCE_MAJORS = (140, 141, 142, 143, 144, 145, 146, 147)
TARGET_MAJORS = (148, 149, 150, 151, 152, 153, 154)

OsName = Literal["linux", "windows", "macos"]

_MOBILE_RE = re.compile(r"Mobile|Android|iPhone|iPad", re.I)
_CHROME_TOKEN_RE = re.compile(r"(Chrome|chrome)/(\d+(?:\.\d+){0,3})")


def is_mobile_ua(text: str) -> bool:
    return bool(_MOBILE_RE.search(text or ""))


def detect_os(text: str) -> OsName | None:
    """Return a platform when the string is clearly one desktop OS."""
    if not text or is_mobile_ua(text):
        return None
    lower = text.lower()
    if "windows nt" in lower or "win64" in lower or "win32" in lower:
        return "windows"
    if "macintosh" in lower or "mac os" in lower:
        return "macos"
    if "linux" in lower or "x11" in lower:
        return "linux"
    return None


def exact_version(major: int, os_name: OsName) -> str | None:
    return CHROME_STABLE.get(os_name, {}).get(major)


def _oses_for_text(text: str) -> tuple[OsName, ...]:
    detected = detect_os(text)
    if detected is not None:
        return (detected,)
    return ("linux", "windows", "macos")


def rewrite_chrome_tokens(text: str, new_major: int) -> list[str]:
    """Desktop Chrome token rewritten to exact Stable ``a.b.c.d`` for *new_major*.

    OS-specific strings (UA) get that OS's build. Bare ``chrome/144.0.0.0``
    tokens get one clone per OS that published that major (Linux has no 154).
    """
    if not text or is_mobile_ua(text):
        return []
    match = _CHROME_TOKEN_RE.search(text)
    if match is None:
        return []
    old_major = int(match.group(2).split(".", 1)[0])
    if old_major not in SOURCE_MAJORS:
        return []
    brand = match.group(1)
    seen: set[str] = set()
    out: list[str] = []
    for os_name in _oses_for_text(text):
        version = exact_version(new_major, os_name)
        if version is None:
            continue
        rewritten = text[: match.start()] + f"{brand}/{version}" + text[match.end() :]
        if rewritten not in seen:
            seen.add(rewritten)
            out.append(rewritten)
    return out


def rewrite_chrome_token(text: str, new_major: int) -> str | None:
    """First exact rewrite, or None. Prefer ``rewrite_chrome_tokens``."""
    tokens = rewrite_chrome_tokens(text, new_major)
    return tokens[0] if tokens else None


def clone_probability_tree(obj: Any) -> Any:
    """Deep-copy dict/list; add cloned keys for each target rewrite; keep originals."""
    if isinstance(obj, list):
        return [clone_probability_tree(x) for x in obj]
    if not isinstance(obj, dict):
        return copy.deepcopy(obj)
    cloned: dict[str, Any] = {}
    extras: dict[str, Any] = {}
    for key, value in obj.items():
        child = clone_probability_tree(value)
        cloned[key] = child
        if isinstance(key, str):
            for major in TARGET_MAJORS:
                for rewritten in rewrite_chrome_tokens(key, major):
                    if rewritten not in cloned and rewritten not in extras:
                        extras[rewritten] = copy.deepcopy(child)
    cloned.update(extras)
    return cloned


def extend_possible_values(values: list[str]) -> list[str]:
    seen = set(values)
    out = list(values)
    for value in values:
        for major in TARGET_MAJORS:
            for rewritten in rewrite_chrome_tokens(value, major):
                if rewritten not in seen:
                    seen.add(rewritten)
                    out.append(rewritten)
    return out


def upgrade_network_definition(net: dict) -> dict:
    upgraded = copy.deepcopy(net)
    for node in upgraded.get("nodes", []):
        if "possibleValues" in node:
            node["possibleValues"] = extend_possible_values(node["possibleValues"])
        if "conditionalProbabilities" in node:
            node["conditionalProbabilities"] = clone_probability_tree(
                node["conditionalProbabilities"]
            )
    return upgraded


def upgrade_helper_lines(lines: list[str]) -> list[str]:
    seen = set(lines)
    out = list(lines)
    for line in lines:
        parts = line.split("|", 1)
        left = parts[0]
        suffix = f"|{parts[1]}" if len(parts) > 1 else ""
        for major in TARGET_MAJORS:
            for rewritten_left in rewrite_chrome_tokens(left, major):
                new_line = rewritten_left + suffix
                if new_line not in seen:
                    seen.add(new_line)
                    out.append(new_line)
    return out


def pack_network_zip(network: dict, zip_path: Path) -> None:
    tmp = zip_path.with_suffix(".zip.tmp")
    payload = json.dumps(network, separators=(",", ":"))
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("network.json", payload)
    tmp.replace(zip_path)


def _load_network(data_dir: Path, name: str) -> dict:
    unpacked = data_dir / "unpacked" / name / "network.json"
    if unpacked.is_file():
        return json.loads(unpacked.read_text(encoding="utf-8"))
    with zipfile.ZipFile(data_dir / f"{name}.zip") as zf:
        return json.loads(zf.read("network.json"))


def _write_network(data_dir: Path, name: str, network: dict) -> None:
    unpacked_dir = data_dir / "unpacked" / name
    unpacked_dir.mkdir(parents=True, exist_ok=True)
    (unpacked_dir / "network.json").write_text(
        json.dumps(network, separators=(",", ":")), encoding="utf-8"
    )
    pack_network_zip(network, data_dir / f"{name}.zip")


def upgrade_datapack_dir(data_dir: Path) -> None:
    data_dir = Path(data_dir)

    header = upgrade_network_definition(_load_network(data_dir, "header-network-definition"))
    _write_network(data_dir, "header-network-definition", header)

    fingerprint = upgrade_network_definition(
        _load_network(data_dir, "fingerprint-network-definition")
    )
    _write_network(data_dir, "fingerprint-network-definition", fingerprint)

    helper_path = data_dir / "browser-helper-file.json"
    if helper_path.is_file():
        lines = json.loads(helper_path.read_text(encoding="utf-8"))
        helper_path.write_text(
            json.dumps(upgrade_helper_lines(lines), separators=(",", ":")),
            encoding="utf-8",
        )

    input_unpacked = data_dir / "unpacked" / "input-network-definition" / "network.json"
    if input_unpacked.is_file():
        input_net = json.loads(input_unpacked.read_text(encoding="utf-8"))
        pack_network_zip(input_net, data_dir / "input-network-definition.zip")
    elif (data_dir / "input-network-definition.zip").is_file():
        with zipfile.ZipFile(data_dir / "input-network-definition.zip") as zf:
            input_net = json.loads(zf.read("network.json"))
        unpacked_dir = data_dir / "unpacked" / "input-network-definition"
        unpacked_dir.mkdir(parents=True, exist_ok=True)
        (unpacked_dir / "network.json").write_text(
            json.dumps(input_net, separators=(",", ":")), encoding="utf-8"
        )
