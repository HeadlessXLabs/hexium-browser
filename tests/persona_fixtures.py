"""Frozen BrowserForge-shaped Linux Chrome rows for persona unit tests."""

from __future__ import annotations

CHROME_149_LINUX_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/149.0.7672.114 Safari/537.36"
)

CHROME_147_WINDOWS_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/147.0.7728.64 Safari/537.36"
)

CHROME_147_WIN_UACH = {
    "brands": [
        {"brand": "Not.A/Brand", "version": "8"},
        {"brand": "Chromium", "version": "147"},
        {"brand": "Google Chrome", "version": "147"},
    ],
    "mobile": False,
    "platform": "Windows",
    "architecture": "x86",
    "bitness": "64",
    "model": "",
    "uaFullVersion": "147.0.7728.64",
    "fullVersionList": [
        {"brand": "Not.A/Brand", "version": "8.0.0.0"},
        {"brand": "Chromium", "version": "147.0.7728.64"},
        {"brand": "Google Chrome", "version": "147.0.7728.64"},
    ],
    "platformVersion": "15.0.0",
}

CHROME_149_UACH = {
    "brands": [
        {"brand": "Not.A/Brand", "version": "8"},
        {"brand": "Chromium", "version": "149"},
        {"brand": "Google Chrome", "version": "149"},
    ],
    "mobile": False,
    "platform": "Linux",
    "architecture": "x86",
    "bitness": "64",
    "model": "",
    "uaFullVersion": "149.0.7672.114",
    "fullVersionList": [
        {"brand": "Not.A/Brand", "version": "8.0.0.0"},
        {"brand": "Chromium", "version": "149.0.7672.114"},
        {"brand": "Google Chrome", "version": "149.0.7672.114"},
    ],
    "platformVersion": "6.8.0",
}


def linux_chrome_149_fingerprint(**overrides: object) -> dict:
    """Return a BrowserForge ``asdict(Fingerprint)``-shaped Linux Chrome row."""
    fp = {
        "screen": {
            "availHeight": 1040,
            "availWidth": 1920,
            "availTop": 0,
            "availLeft": 0,
            "colorDepth": 24,
            "height": 1080,
            "pixelDepth": 24,
            "width": 1920,
            "devicePixelRatio": 1.0,
            "pageXOffset": 0,
            "pageYOffset": 0,
            "innerHeight": 952,
            "outerHeight": 1040,
            "outerWidth": 1920,
            "innerWidth": 1920,
            "screenX": 0,
            "clientWidth": 1920,
            "clientHeight": 952,
            "hasHDR": False,
        },
        "navigator": {
            "userAgent": CHROME_149_LINUX_UA,
            "userAgentData": dict(CHROME_149_UACH),
            "doNotTrack": None,
            "appCodeName": "Mozilla",
            "appName": "Netscape",
            "appVersion": "5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/149.0.7672.114 Safari/537.36",
            "oscpu": "",
            "webdriver": False,
            "language": "en-US",
            "languages": ["en-US", "en"],
            "platform": "Linux x86_64",
            "deviceMemory": 8,
            "hardwareConcurrency": 8,
            "product": "Gecko",
            "productSub": "20030107",
            "vendor": "Google Inc.",
            "vendorSub": "",
            "maxTouchPoints": 0,
            "extraProperties": {},
        },
        "headers": {
            "User-Agent": CHROME_149_LINUX_UA,
            "Accept-Language": "en-US,en;q=0.9",
        },
        "videoCodecs": {},
        "audioCodecs": {},
        "pluginsData": {},
        "battery": {"charging": True, "chargingTime": 0, "dischargingTime": None, "level": 1},
        "videoCard": {
            "vendor": "Google Inc. (Intel)",
            "renderer": "ANGLE (Intel, Mesa Intel(R) UHD Graphics 630 (CFL GT2), OpenGL 4.6)",
        },
        "multimediaDevices": [],
        "fonts": ["DejaVu Sans", "Noto Sans", "Liberation Sans"],
        "mockWebRTC": False,
        "slim": False,
    }
    for key, value in overrides.items():
        if key in ("screen", "navigator", "videoCard") and isinstance(value, dict):
            fp[key] = {**fp[key], **value} if isinstance(fp[key], dict) else value
        else:
            fp[key] = value
    return fp


def windows_chrome_147_fingerprint(**overrides: object) -> dict:
    """Return a Hexium-network-shaped Windows Chrome desktop row."""
    fp = {
        "screen": {
            "availHeight": 1040,
            "availWidth": 1920,
            "availTop": 0,
            "availLeft": 0,
            "colorDepth": 24,
            "height": 1080,
            "pixelDepth": 24,
            "width": 1920,
            "devicePixelRatio": 1.0,
            "pageXOffset": 0,
            "pageYOffset": 0,
            "innerHeight": 952,
            "outerHeight": 1040,
            "outerWidth": 1920,
            "innerWidth": 1920,
            "screenX": 0,
            "clientWidth": 1920,
            "clientHeight": 952,
            "hasHDR": False,
        },
        "navigator": {
            "userAgent": CHROME_147_WINDOWS_UA,
            "userAgentData": dict(CHROME_147_WIN_UACH),
            "doNotTrack": None,
            "appCodeName": "Mozilla",
            "appName": "Netscape",
            "appVersion": "5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/147.0.7728.64 Safari/537.36",
            "oscpu": "",
            "webdriver": False,
            "language": "en-US",
            "languages": ["en-US", "en"],
            "platform": "Win32",
            "deviceMemory": 8,
            "hardwareConcurrency": 8,
            "product": "Gecko",
            "productSub": "20030107",
            "vendor": "Google Inc.",
            "vendorSub": "",
            "maxTouchPoints": 0,
            "extraProperties": {},
        },
        "headers": {
            "User-Agent": CHROME_147_WINDOWS_UA,
            "Accept-Language": "en-US,en;q=0.9",
        },
        "videoCodecs": {},
        "audioCodecs": {},
        "pluginsData": {},
        "battery": {"charging": True, "chargingTime": 0, "dischargingTime": None, "level": 1},
        "videoCard": {
            "vendor": "Google Inc. (NVIDIA)",
            "renderer": (
                "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 "
                "ps_5_0, D3D11)"
            ),
        },
        "multimediaDevices": [],
        "fonts": ["Arial", "Calibri", "Segoe UI", "Times New Roman", "Consolas"],
        "mockWebRTC": False,
        "slim": False,
    }
    for key, value in overrides.items():
        if key in ("screen", "navigator", "videoCard") and isinstance(value, dict):
            merged = {**fp[key], **value} if isinstance(fp[key], dict) else value
            if key == "navigator" and "userAgentData" in value and isinstance(value["userAgentData"], dict):
                merged["userAgentData"] = {
                    **fp["navigator"]["userAgentData"],
                    **value["userAgentData"],
                }
            fp[key] = merged
        else:
            fp[key] = value
    return fp
