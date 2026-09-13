from hexium_browser.persona.rewrite_ua import chrome_major_from_ua
from hexium_browser.persona.sample import (
    _linux_device_row_sampler,
    _sampled_chrome_major_ok,
    _windows_device_row_sampler,
)
from hexium_browser.persona.schema import MAX_HARDWARE_CONCURRENCY, MIN_SAMPLED_CHROME_MAJOR
from hexium_browser.persona.sampler.headers import Browser


def test_constants():
    assert MIN_SAMPLED_CHROME_MAJOR == 140
    assert MAX_HARDWARE_CONCURRENCY == 32


def test_chrome_major_from_modern_ua():
    ua = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/144.0.7559.95 Safari/537.36"
    )
    assert chrome_major_from_ua(ua) == 144


def test_chrome_major_from_ancient_ua():
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"
    )
    assert chrome_major_from_ua(ua) == 39


def test_chrome_major_missing():
    assert chrome_major_from_ua("Mozilla/5.0 (compatible; bot)") is None


def test_linux_sampler_requests_chrome_min_140():
    gen = _linux_device_row_sampler()
    browsers = gen.header_generator.options["browsers"]
    assert len(browsers) == 1
    assert isinstance(browsers[0], Browser)
    assert browsers[0].name == "chrome"
    assert browsers[0].min_version == 140
    assert browsers[0].max_version is None
    assert gen.header_generator.options["os"] == ("linux",)
    assert gen.header_generator.options["devices"] == ("desktop",)


def test_windows_sampler_requests_chrome_min_140():
    gen = _windows_device_row_sampler()
    browsers = gen.header_generator.options["browsers"]
    assert browsers[0].name == "chrome"
    assert browsers[0].min_version == 140
    assert browsers[0].max_version is None
    assert gen.header_generator.options["os"] == ("windows",)
    assert gen.header_generator.options["devices"] == ("desktop",)


def test_sampled_row_rejects_chrome_39():
    raw = {
        "navigator": {
            "userAgent": "Mozilla/5.0 Chrome/39.0.2171.95 Safari/537.36",
            "hardwareConcurrency": 8,
        }
    }
    assert _sampled_chrome_major_ok(raw) is False


def test_sampled_row_accepts_chrome_144():
    raw = {
        "navigator": {
            "userAgent": "Mozilla/5.0 Chrome/144.0.7559.95 Safari/537.36",
            "hardwareConcurrency": 8,
        }
    }
    assert _sampled_chrome_major_ok(raw) is True


def test_sampled_row_rejects_384_cores():
    raw = {
        "navigator": {
            "userAgent": "Mozilla/5.0 Chrome/144.0.0.0 Safari/537.36",
            "hardwareConcurrency": 384,
        }
    }
    assert _sampled_chrome_major_ok(raw) is False
