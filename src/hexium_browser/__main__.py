"""CLI for hexium_browser — fetch and inspect the Hexium Chromium binary."""

from __future__ import annotations

import argparse
import importlib.util
import logging
import os
import platform
import subprocess
import sys


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stderr,
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


def cmd_fetch(args: argparse.Namespace) -> None:
    from .download import ensure_binary

    path = ensure_binary(allow_download=True)
    print(path)


def cmd_install(args: argparse.Namespace) -> None:
    cmd_fetch(args)


def _module_available(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _binary_version(binary_path: str) -> tuple[bool, str, str]:
    argv = [binary_path, "--version"]
    if platform.system() == "Windows":
        argv.append("--no-startup-window")
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, "", str(exc)
    if result.returncode != 0:
        return False, "", (result.stderr or result.stdout).strip()
    return True, result.stdout.strip(), ""


def _collect_diagnostics(quick: bool, proxy: str | None = None) -> dict:
    from ._version import __version__
    from .config import get_platform_tag
    from .download import binary_info

    diag: dict = {
        "environment": {
            "wrapper": __version__,
            "python": sys.version.split()[0],
            "os": platform.system(),
            "arch": platform.machine(),
        }
    }
    try:
        diag["environment"]["platform_tag"] = get_platform_tag()
    except Exception as exc:
        diag["environment"]["platform_tag"] = f"unavailable ({exc})"

    diag["binary"] = binary_info()

    binary = diag["binary"].get("binary_path")
    installed = diag["binary"].get("installed")
    if quick:
        diag["launch"] = {"tested": False, "reason": "skipped (--quick)"}
    elif not binary or not installed:
        diag["launch"] = {"tested": False, "reason": "binary not installed"}
    else:
        ok, version, err = _binary_version(binary)
        diag["launch"] = {"tested": True, "ok": ok, "version": version, "error": err}

    from .geoip import GEOIP_DB_FILENAME, _get_geoip_dir

    db_path = _get_geoip_dir() / GEOIP_DB_FILENAME
    diag["geoip"] = {"db_present": db_path.exists(), "path": str(db_path)}

    if proxy:
        try:
            from .geoip import resolve_proxy_geo_with_ip

            tz, locale, exit_ip = resolve_proxy_geo_with_ip(proxy)
            diag["geoip"]["resolved"] = {
                "exit_ip": exit_ip,
                "timezone": tz,
                "locale": locale,
            }
        except ImportError:
            diag["geoip"]["resolved"] = {"error": "geoip2 not installed"}
        except Exception as exc:
            diag["geoip"]["resolved"] = {"error": str(exc)}

    diag["modules"] = {
        label: _module_available(module)
        for label, module in {
            "playwright": "playwright.sync_api",
            "geoip2": "geoip2.database",
        }.items()
    }
    return diag


def _print_diagnostics(diag: dict) -> None:
    env = diag["environment"]
    print("Hexium browser diagnostics")
    print(f"Wrapper:   {env['wrapper']}")
    print(f"Python:    {env['python']}")
    print(f"OS:        {env['os']} {env['arch']}")
    print(f"Platform:  {env.get('platform_tag', 'unknown')}")

    binary = diag["binary"]
    print(f"Version:   {binary.get('version')}")
    print(f"Source:    {binary.get('source', 'cache')}")
    print(f"Binary:    {binary.get('binary_path')}")
    print(f"Installed: {binary.get('installed')}")
    if binary.get("cache_dir"):
        print(f"Cache:     {binary['cache_dir']}")
        print(f"Download:  {binary.get('download_url')}")
        if binary.get("github_download_url"):
            print(f"GitHub:    {binary['github_download_url']}")

    launch = diag["launch"]
    if not launch.get("tested"):
        print(f"Launch:    {launch['reason']}")
    elif launch["ok"]:
        print(f"Launch:    ok — {launch['version'] or 'runs'}")
    else:
        print(f"Launch:    failed — {launch['error']}")

    geoip = diag["geoip"]
    print(f"GeoIP DB:  {'present' if geoip['db_present'] else 'not downloaded'}")
    resolved = geoip.get("resolved")
    if resolved:
        if resolved.get("error"):
            print(f"Exit IP:   (could not resolve — {resolved['error']})")
        else:
            print(f"Exit IP:   {resolved.get('exit_ip') or '(unknown)'}")
            print(f"Timezone:  {resolved.get('timezone') or '(unknown)'}")
            print(f"Locale:    {resolved.get('locale') or '(unknown)'}")

    print("Modules:")
    for label, available in diag["modules"].items():
        print(f"  {label}: {'ok' if available else 'missing'}")


def cmd_info(args: argparse.Namespace) -> None:
    quick = getattr(args, "quick", False)
    diag = _collect_diagnostics(quick=quick, proxy=getattr(args, "proxy", None))
    if getattr(args, "json", False):
        import json

        print(json.dumps(diag, indent=2))
    else:
        _print_diagnostics(diag)


def cmd_clear_cache(args: argparse.Namespace) -> None:
    from .config import get_cache_dir
    from .download import clear_cache

    if not get_cache_dir().exists():
        print("No cache to clear.")
        return
    clear_cache()
    print("Cache cleared.")


def _explicit_last_profile_name() -> str | None:
    from .profiles import load_config

    value = load_config().get("last_profile")
    if not isinstance(value, str):
        return None
    name = value.strip()
    return name or None


def cmd_profiles(args: argparse.Namespace) -> None:
    from .profiles import (
        ensure_profile,
        get_last_profile_name,
        list_profile_names,
        profile_dir,
        set_last_profile_name,
    )

    action = getattr(args, "profiles_cmd", None) or "list"
    if action == "list":
        last = get_last_profile_name()
        explicit_last = _explicit_last_profile_name()
        for name in list_profile_names():
            suffix = " (last)" if explicit_last is not None and name == last else ""
            print(f"{name}{suffix}")
        return
    if action == "new":
        name = getattr(args, "name", None)
        if not name:
            raise ValueError("profiles new requires a name")
        path = ensure_profile(name)
        print(path)
        return
    if action == "use":
        name = getattr(args, "name", None)
        if not name:
            raise ValueError("profiles use requires a name")
        path = profile_dir(name)
        if not path.is_dir():
            raise FileNotFoundError(f"profile {name!r} not found at {path}")
        set_last_profile_name(name)
        print(path)
        return
    if action == "last":
        name = _explicit_last_profile_name()
        if not name:
            raise FileNotFoundError(
                "no last named profile; run: hexium-browser profiles use NAME"
            )
        print(profile_dir(name))
        return
    raise ValueError(f"unknown profiles command {action!r}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="hexium-browser",
        description="Manage the Hexium stealth Chromium binary.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("fetch", help="Ensure the Hexium binary is available")
    sub.add_parser("install", help="Alias for fetch")

    def _add_info_flags(p: argparse.ArgumentParser) -> None:
        p.add_argument("--quick", action="store_true", help="Skip launch test")
        p.add_argument("--json", action="store_true", help="Emit diagnostics as JSON")
        p.add_argument("--proxy", metavar="URL", help="Resolve geoip for this proxy")

    _add_info_flags(sub.add_parser("info", help="Environment + binary diagnostics"))
    _add_info_flags(sub.add_parser("doctor", help="Alias for info"))
    sub.add_parser("clear-cache", help="Remove cached binaries")

    profiles_p = sub.add_parser(
        "profiles", help="List and select persistent Hexium profiles"
    )
    profiles_sub = profiles_p.add_subparsers(dest="profiles_cmd")
    profiles_sub.add_parser("list", help="List profile names")
    new_p = profiles_sub.add_parser("new", help="Create a named profile directory")
    new_p.add_argument("name")
    use_p = profiles_sub.add_parser("use", help="Set last_profile")
    use_p.add_argument("name")
    profiles_sub.add_parser("last", help="Print the last named profile path")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(2)

    _setup_logging()

    commands = {
        "fetch": cmd_fetch,
        "install": cmd_install,
        "info": cmd_info,
        "doctor": cmd_info,
        "clear-cache": cmd_clear_cache,
        "profiles": cmd_profiles,
    }

    try:
        commands[args.command](args)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
