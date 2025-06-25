"""
context.py – create a Playwright **BrowserContext** with a JavaScript and
network fingerprint that matches the supplied User‑Agent string. This version
adds deeper stealth patches: navigator.userAgentData, navigator.webdriver,
WebRTC/mediaDevices, touch APIs, improved canvas noise and randomised WebGL
vendor/renderer.
"""

from __future__ import annotations

import asyncio
import json
import random
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from playwright.async_api import Browser, BrowserContext, Playwright

# ──────────────────────────────
# Optional: httpagentparser for robust engine detection
# ──────────────────────────────
try:
    import httpagentparser  # type: ignore
    _HAS_HTTPAGENT = True
except ImportError:  # library not installed – fallback to simple rules
    _HAS_HTTPAGENT = False

# ──────────────────────────────
# playwright‑stealth poly‑loader (Chromium only)
# ──────────────────────────────

async def _build_apply_stealth():
    try:  # Stealth ≥ 2 – class API
        Stealth = getattr(import_module("playwright_stealth"), "Stealth")  # type: ignore[attr-defined]
        stealth_inst = Stealth(init_scripts_only=True)

        async def _apply(ctx):
            await stealth_inst.apply_stealth_async(ctx)

        return _apply
    except Exception:
        for fname in ("stealth_async", "stealth"):
            try:
                func = getattr(import_module("playwright_stealth"), fname)  # type: ignore[attr-defined]
                break
            except Exception:
                func = None
        if func is None:
            async def _apply(_: BrowserContext):
                return
            return _apply

        async def _apply(ctx, _f=func):
            await _f(ctx)
        return _apply

_loop = (
    asyncio.get_event_loop()
    if asyncio.get_event_loop_policy().get_event_loop()
    else asyncio.new_event_loop()
)
_apply_stealth = _loop.run_until_complete(_build_apply_stealth())

# ──────────────────────────────
# Local helpers & resources
# ──────────────────────────────

from .clienthints import (  # noqa: E402 – after shim
    extract_high_entropy_hints,
    parse_chromium_full_version,
    parse_chromium_ua,
    parse_chromium_version,
)

_JS_DIR = Path(__file__).resolve().parent / "js"
_JS_TEMPLATE_PATH = _JS_DIR / "spoof_useragent.js"
_EXTRA_STEALTH_PATH = _JS_DIR / "extra_stealth.js"
_FWK_STEALTH_PATH = _JS_DIR / "fwk_stealth.js"
_CHROMIUM_STEALTH_PATH = _JS_DIR / "chromium_stealth.js"

_JS_TEMPLATE = _JS_TEMPLATE_PATH.read_text(encoding="utf-8")
_EXTRA_STEALTH = _EXTRA_STEALTH_PATH.read_text(encoding="utf-8")
_FWK_STEALTH_TEMPLATE = _FWK_STEALTH_PATH.read_text(encoding="utf-8")
_CHROMIUM_STEALTH_TEMPLATE = _CHROMIUM_STEALTH_PATH.read_text(encoding="utf-8")

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

_MEM_CHOICES = [4, 6, 8, 12, 16, 24, 32]  # in GiB
_CORE_CHOICES = [4, 6, 8, 12, 16]

# Real WebGL vendor/renderer pairs sourced from real‑world hardware.
_WEBGL_CHOICES: Tuple[Tuple[str, str], ...] = (
    ("Google Inc.", "ANGLE (Intel(R) UHD Graphics 630)"),
    ("Google Inc.", "ANGLE (NVIDIA GeForce RTX 3060 Laptop GPU Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc.", "ANGLE (AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc.", "ANGLE (Apple M1 Pro)"),
)

_WEBGL_BY_OS = {
    "windows": (
        ("NVIDIA Corporation", "NVIDIA GeForce RTX 3060/PCIe/SSE2"),
        ("Intel",              "Intel(R) UHD Graphics 630"),
        ("AMD",                "AMD Radeon RX 6800 XT"),
    ),
    "mac": (
        ("Apple Inc.",         "Apple M1 Pro"),
    ),
    "linux": (
        ("Intel",              "Mesa Intel(R) UHD Graphics 630"),
        ("AMD",                "AMD Radeon RX 6800 XT (RADV NAVI21)"),
    ),
}

def _pick_webgl_pair(ua: str) -> Tuple[str, str]:
    """Return a realistic (vendor, renderer) pair based on the OS detected in the UA."""
    low = ua.lower()
    if "mac os" in low or "macos" in low:
        pool = _WEBGL_BY_OS["mac"]
    elif "windows" in low:
        pool = _WEBGL_BY_OS["windows"]
    else:
        pool = _WEBGL_BY_OS["linux"]
    return random.choice(pool)

_SCREEN_CHOICES: Tuple[Tuple[int, int], ...] = (
    (1920, 1080),
    (2560, 1440),
    (1366, 768),
    (1536, 864),
    (2880, 1800),
)


def _engine_from_ua(ua: str) -> str:
    """Best‑effort engine detection from UA string."""
    if _HAS_HTTPAGENT:
        parsed = httpagentparser.detect(ua)  # type: ignore
        browser = (parsed.get("browser") or {})
        name = (browser.get("name") or "").lower()
        if "firefox" in name:
            return "firefox"
        if "safari" in name and "chrome" not in name:
            return "webkit"
        return "chromium"
    # fallback heuristic
    low = ua.lower()
    if "firefox" in low and "seamonkey" not in low:
        return "firefox"
    if "safari" in low and "chrome" not in low and "chromium" not in low:
        return "webkit"
    return "chromium"


def _locale_from_gate(gate_args: Dict[str, Any]) -> Tuple[str, Tuple[str, ...]]:
    raw = gate_args.get("LanguageGate", {}).get("accept_language") if gate_args else None
    if not raw:
        return "en-US", ("en-US", "en")
    primary = raw.split(",", 1)[0].strip()
    return primary, (primary, primary.split("-", 1)[0])


def _timezone_from_gate(gate_args: Dict[str, Any]) -> str:
    return gate_args.get("GeolocationGate", {}).get("timezone_id", "UTC")


# ──────────────────────────────
# JS patch builder for Firefox / WebKit
# ──────────────────────────────

def _fwk_js_patch(languages: Tuple[str, ...], tz: str, mem: int, cores: int, ua: str) -> str:
    lang_js = json.dumps(list(languages))
    return (_FWK_STEALTH_TEMPLATE
            .replace('__LANG_JS__', lang_js)
            .replace('__TZ__', tz))


# ──────────────────────────────
# Public API
# ──────────────────────────────

async def create_context(
    playwright: Playwright,
    gate_args: Optional[Dict[str, Any]] = None,
) -> Tuple[Browser, BrowserContext]:
    """Launch a browser context whose engine and JS surfaces align with the UA."""

    gate_args = gate_args or {}

    ua: str = gate_args.get("UserAgentGate", {}).get("user_agent", _DEFAULT_UA)
    locale, languages = _locale_from_gate(gate_args)
    tz_id = _timezone_from_gate(gate_args)

    engine = _engine_from_ua(ua)

    # Random hardware specs each run
    rand_mem = random.choice(_MEM_CHOICES)
    rand_cores = random.choice(_CORE_CHOICES)

    # Choose screen resolution
    screen_w, screen_h = random.choice(_SCREEN_CHOICES)

    # Choose WebGL vendor/renderer (Chromium only)
    webgl_vendor, webgl_renderer = _pick_webgl_pair(ua)

    # Chromium‑specific high‑entropy hints
    if engine == "chromium":
        entropy = extract_high_entropy_hints(ua)
        brand, brand_v = parse_chromium_ua(ua)
        chromium_v = parse_chromium_version(ua)
        mobile_flag = "mobile" in ua.lower()
    else:
        entropy = {}
        brand = brand_v = chromium_v = ""
        mobile_flag = False

    fp: Dict[str, Any] = {
        "ua": ua,
        "languages": languages,
        "tz": tz_id,
        "mem": rand_mem,
        "cores": rand_cores,
        "screen": (screen_w, screen_h),
        "webgl_vendor": webgl_vendor,
        "webgl_renderer": webgl_renderer,
    }
    if engine == "chromium":
        fp.update(
            brand=brand,
            brand_v=brand_v,
            ua_full_version=parse_chromium_full_version(ua) or chromium_v,
            platform=entropy.get("platform", "Win32"),
            platform_version=entropy.get("platformVersion", "15.0"),
            arch=entropy.get("architecture", "x86"),
            bitness=entropy.get("bitness", "64"),
            wow64=entropy.get("wow64", False),
            mobile=mobile_flag,
        )

    # Launch correct engine
    launcher = getattr(playwright, engine)
    browser: Browser = await launcher.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"] if engine == "chromium" else [],
    )

    ctx_args: Dict[str, Any] = {
        "user_agent": fp["ua"],
        "locale": locale,
        "timezone_id": fp["tz"],
        "viewport": {"width": screen_w, "height": screen_h},
        "screen": {"width": screen_w, "height": screen_h},
    }
    geo = gate_args.get("GeolocationGate", {}).get("geolocation")
    if geo is not None:
        ctx_args["geolocation"] = geo

    context: BrowserContext = await browser.new_context(**ctx_args)

    # ───────── Chromium path ─────────
    if engine == "chromium":
        await _apply_stealth(context)

        lang_js = json.dumps(list(fp["languages"]))
        touch_js = """if ('ontouchstart' in window) {} else Object.defineProperty(window, 'ontouchstart', {value: null});"""
        if fp.get("mobile"):
            touch_js = "Object.defineProperty(window, 'ontouchstart', {value: null});"

        js_script = _JS_TEMPLATE.format(
            chromium_v=chromium_v or "",
            brand=fp["brand"],
            brand_v=fp["brand_v"],
            architecture=fp.get("arch", "x86"),
            bitness=fp.get("bitness", "64"),
            wow64=str(bool(fp.get("wow64", False))).lower(),
            model=entropy.get("model", ""),
            mobile=str(fp.get("mobile", False)).lower(),
            platform=fp.get("platform", "Win32"),
            platformVersion=fp.get("platform_version", "15.0"),
            uaFullVersion=fp.get("ua_full_version", chromium_v),
        )

        chromium_patch = (_CHROMIUM_STEALTH_TEMPLATE
            .replace('__LANG_JS__', lang_js)
            .replace('__TOUCH_JS__', touch_js)
            .replace('__BRAND__', fp['brand'])
            .replace('__BRAND_V__', fp['brand_v'])
            .replace('__PLATFORM__', fp['platform'])
            .replace('__MOBILE__', str(fp['mobile']).lower())
            .replace('__ARCH__', fp.get('arch', 'x86'))
            .replace('__BITNESS__', fp.get('bitness', '64'))
            .replace('__MODEL__', entropy.get('model', ''))
            .replace('__PLATFORM_VERSION__', fp.get('platform_version', '15.0'))
            .replace('__UA_FULL_VERSION__', fp.get('ua_full_version', chromium_v))
            .replace('__WOW64__', str(bool(fp.get('wow64', False))).lower())
            .replace('__WEBGL_VENDOR__', webgl_vendor)
            .replace('__WEBGL_RENDERER__', webgl_renderer)
            .replace('__USER_AGENT__', ua)
            .replace('__RAND_MEM__', str(rand_mem))
            .replace('__TZ__', tz_id)
        )
        js_script += chromium_patch

        js_script += _EXTRA_STEALTH
        await context.add_init_script(js_script)

    # ───────── Firefox / WebKit path ─────────
    else:
        js_script = _fwk_js_patch(languages, fp["tz"], rand_mem, rand_cores, ua)
        js_script += _EXTRA_STEALTH
        await context.add_init_script(js_script)

    return browser, context




# ──────────────────────────────────────────────────────────
# quick manual CLI test
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    from playwright.async_api import async_playwright

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ua",
        default=_DEFAULT_UA,
        help="User-Agent string to emulate (full header value)",
    )
    args = parser.parse_args()

    async def _demo():
        async with async_playwright() as p:
            browser, ctx = await create_context(
                p, {"UserAgentGate": {"user_agent": args.ua}}
            )
            page = await ctx.new_page()
            await page.goto("https://httpbin.org/headers")
            print(await page.text_content("pre"))
            await browser.close()

    asyncio.run(_demo())
