"""
context.py – create a Playwright **BrowserContext** with a JavaScript and
network fingerprint that consistently matches the supplied User‑Agent string.

Uses *base profiles* instead of picking each hardware trait
independently.  A base profile is a small template that describes valid
ranges/pools for RAM, CPU cores, screen size and WebGL strings.  One profile
is selected per run based on the UA’s OS family and form‑factor, then random
values are drawn only from that profile – keeping the overall fingerprint
coherent while still varied.
"""
from src.clienthints import parse_chromium_ua, parse_chromium_version, parse_chromium_full_version

"""
context.py – create a Playwright **BrowserContext** with a JavaScript and
network fingerprint that consistently matches the supplied User‑Agent string.

Uses *base profiles* instead of picking each hardware trait
independently.  A base profile is a small template that describes valid
ranges/pools for RAM, CPU cores, screen size and WebGL strings.  One profile
is selected per run based on the UA’s OS family and form‑factor, then random
values are drawn only from that profile – keeping the overall fingerprint
coherent while still varied.
"""

import asyncio
import json
import random
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

        async def _apply(ctx: BrowserContext):
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

        async def _apply(ctx: BrowserContext, _f=func):
            await _f(ctx)

        return _apply

_apply_stealth = asyncio.run(_build_apply_stealth())

# ──────────────────────────────
# JS templates & extras
# ──────────────────────────────

_JS_DIR = Path(__file__).resolve().parent / "js"
_JS_TEMPLATE_PATH = _JS_DIR / "spoof_useragent.js"
_EXTRA_STEALTH_PATH = _JS_DIR / "extra_stealth.js"
_FWK_STEALTH_PATH = _JS_DIR / "fwk_stealth.js"
_CHROMIUM_STEALTH_PATH = _JS_DIR / "chromium_stealth.js"
_WEBGL_PATCH_PATH = _JS_DIR / "webgl_patch.js"

_JS_TEMPLATE = _JS_TEMPLATE_PATH.read_text(encoding="utf-8")
_EXTRA_STEALTH = _EXTRA_STEALTH_PATH.read_text(encoding="utf-8")
_FWK_STEALTH_TEMPLATE = _FWK_STEALTH_PATH.read_text(encoding="utf-8")
_CHROMIUM_STEALTH_TEMPLATE = _CHROMIUM_STEALTH_PATH.read_text(encoding="utf-8")
_WEBGL_PATCH_TEMPLATE = _WEBGL_PATCH_PATH.read_text(encoding="utf-8")

# General stealth – pruned list (headed window makes most old patches redundant)
_EXTRA_JS_FILES = [
    "font_mask.js",
    "webrtc_leak_block.js",
    "network_info_stub.js",  # only used for mobile‑UA profiles
    "performance_timing.js",
    "incognito.js",
    "speech_synthesis_stub.js"
]

_EXTRA_JS_SNIPPETS = {
    name: (_JS_DIR / name).read_text("utf-8") for name in _EXTRA_JS_FILES
}

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# ──────────────────────────────
# Base‑profile table
#   Each profile contains ranges / pools, NOT fixed single values.
#   Add or adjust profiles as needed – selection logic will pick one per run.
# ──────────────────────────────

_BASE_PROFILES: List[Dict[str, Any]] = [
    # ------------------------------------------------------ desktop low
    {
        "id": "desk_low",
        "os": ["windows", "linux"],
        "class": "desktop",
        "mem": [2, 4, 6, 8, 12],                      # GiB
        "cores": [2, 4, 6],                           # logical cores
        "screen": [                                   # common 16∶9 / 16∶10 HD
            (1280, 720), (1280, 800), (1366, 768),
            (1440, 900), (1536, 864)
        ],
        "webgl": [                                    # integrated GPUs (2012‑2018)
            ("Intel", "Intel(R) HD Graphics 4000"),
            ("Intel", "Intel(R) HD Graphics 4600"),
            ("Intel", "Intel(R) HD Graphics 5500"),
            ("Intel", "Intel(R) HD Graphics 620"),
            ("Intel", "Intel(R) UHD Graphics 600"),
        ],
    },
    # ------------------------------------------------------ desktop mid
    {
        "id": "desk_mid",
        "os": ["windows", "linux"],
        "class": "desktop",
        "mem": [8, 12, 16, 24],
        "cores": [4, 6, 8, 10],
        "screen": [                                   # FHD & WFHD
            (1600, 900), (1920, 1080), (1920, 1200),
            (2560, 1080), (2560, 1440)
        ],
        "webgl": [                                    # mid‑tier dGPUs & newer iGPUs
            ("NVIDIA Corporation", "NVIDIA GeForce GTX 1050/PCIe/SSE2"),
            ("NVIDIA Corporation", "NVIDIA GeForce GTX 1650/PCIe/SSE2"),
            ("AMD", "AMD Radeon RX 570 Series"),
            ("AMD", "AMD Radeon RX 6600"),
            ("Intel", "Intel(R) Iris(R) Xe Graphics"),
        ],
    },
    # ------------------------------------------------------ desktop high
    {
        "id": "desk_high",
        "os": ["windows"],
        "class": "desktop",
        "mem": [16, 24, 32, 48, 64, 96, 128],
        "cores": [8, 12, 16, 20, 24, 32],
        "screen": [                                   # QHD‑UHD & ultrawide
            (2560, 1440), (3440, 1440), (3840, 1600),
            (3840, 2160), (5120, 2160), (5120, 2880),
            (7680, 4320),
        ],
        "webgl": [                                    # recent RTX / RX GPUs
            ("NVIDIA Corporation", "NVIDIA GeForce RTX 3060/PCIe/SSE2"),
            ("NVIDIA Corporation", "NVIDIA GeForce RTX 4070/PCIe/SSE2"),
            ("NVIDIA Corporation", "NVIDIA GeForce RTX 4090/PCIe/SSE2"),
            ("AMD", "AMD Radeon RX 6800 XT"),
            ("AMD", "AMD Radeon RX 7900 XTX"),
        ],
    },
    # ------------------------------------------------------ mac laptop (M‑series + Intel)
    {
        "id": "mac_notch",
        "os": ["mac"],
        "class": "laptop",
        "mem": [8, 16, 24, 32, 64],
        "cores": [8, 10, 12],
        "screen": [                                   # Retina & Liquid Retina
            (2560, 1600), (2560, 1664), (2880, 1800), (2880, 1864),
            (3024, 1964), (3456, 2234)
        ],
        "webgl": [                                    # Intel, AMD dGPU, Apple Silicon
            ("Apple Inc.", "Intel Iris Plus Graphics 640"),
            ("Apple Inc.", "AMD Radeon Pro 560X"),
            ("Apple Inc.", "Apple M1"),
            ("Apple Inc.", "Apple M2"),
            ("Apple Inc.", "Apple M3"),
        ],
    },
    # ------------------------------------------------------ ChromeOS laptop
    {
        "id": "chrome_book",
        "os": ["chromeos"],
        "class": "laptop",
        "mem": [4, 8, 16],
        "cores": [4, 8],
        "screen": [                                   # typical Chromebook sizes
            (1366, 768), (1920, 1080), (2256, 1504),
        ],
        "webgl": [
            ("Google Inc.", "ANGLE (Intel, Intel(R) UHD Graphics 600, Direct3D11)"),
            ("Google Inc.", "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics, Direct3D11)"),
        ],
    },
    # ------------------------------------------------------ mobile high‑end phones
    {
        "id": "mobile_high",
        "os": ["android", "ios"],
        "class": "phone",
        "mem": [4, 6, 8, 12],                         # GiB reported via JS API (rounded)
        "cores": [3, 4, 6, 8, 10, 12],                # logical
        "screen": [                                   # CSS‑px @100% zoom, DPR = 3
            (1179, 2556),   # iPhone 15 Pro
            (1290, 2796),   # iPhone 15 Pro Max
            (1080, 2340),   # Galaxy S24
            (1152, 2436),   # Pixel 8
        ],
        "webgl": [                                    # modern mobile GPUs
            ("Qualcomm", "Adreno (TM) 740"),
            ("Qualcomm", "Adreno (TM) 750"),
            ("Arm", "Mali-G715"),
            ("Apple Inc.", "Apple A17"),
        ],
    },
]

# ──────────────────────────────
# Additional helpers
# ──────────────────────────────

def _ua_os_family(ua: str) -> str:
    """Rough OS family detection for base‑profile filtering."""
    low = ua.lower()
    if "windows" in low:
        return "windows"
    if "mac os" in low or "macos" in low:
        return "mac"
    if "android" in low:
        return "android"
    if any(tok in low for tok in ("iphone", "ipad", "ios")):
        return "ios"
    if "cros" in low or "chrome os" in low:
        return "chromeos"
    return "linux"


def _select_base_profile(ua: str) -> Dict[str, Any]:
    os_family = _ua_os_family(ua)
    candidates = [p for p in _BASE_PROFILES if os_family in p["os"]]
    if not candidates:
        candidates = _BASE_PROFILES  # fallback – shouldn’t happen
    return random.choice(candidates)


# Keep the original detailed WebGL pools for fallback use.
_WEBGL_BY_OS = {
    "windows": (
        ("NVIDIA Corporation", "NVIDIA GeForce RTX 3060/PCIe/SSE2"),
        ("NVIDIA Corporation", "NVIDIA GeForce GTX 1060/PCIe/SSE2"),
        ("NVIDIA Corporation", "NVIDIA GeForce GTX 1650/PCIe/SSE2"),
        ("Intel", "Intel(R) HD Graphics 530"),
        ("Intel", "Intel(R) Iris(R) Xe Graphics"),
        ("AMD", "AMD Radeon RX 580"),
        ("AMD", "AMD Radeon RX 6700 XT"),
    ),
    "mac": (
        ("Apple Inc.", "Apple M1"),
        ("Apple Inc.", "Apple M2"),
        ("Apple Inc.", "AMD Radeon Pro 560X"),
    ),
    "linux": (
        ("Intel", "Mesa Intel(R) UHD Graphics 620 (KBL GT2)"),
        ("AMD", "AMD Radeon RX 570 Series (POLARIS10, DRM 3.35.0, 5.4.0-42-generic, LLVM 10.0.0)"),
        ("NVIDIA Corporation", "NVIDIA GeForce RTX 3060/PCIe/SSE2"),
    ),
}


def _pick_webgl_pair(ua: str) -> Tuple[str, str]:
    """Fallback WebGL pair based on UA‑detected OS."""
    fam = _ua_os_family(ua)
    if fam == "mac":
        pool = _WEBGL_BY_OS["mac"]
    elif fam == "windows":
        pool = _WEBGL_BY_OS["windows"]
    else:
        pool = _WEBGL_BY_OS["linux"]
    return random.choice(pool)


# ──────────────────────────────
# Heuristic engine detection
# ──────────────────────────────

def _engine_from_ua(ua: str) -> str:
    """Return 'chromium', 'firefox' or 'webkit'."""
    if _HAS_HTTPAGENT:
        parsed = httpagentparser.detect(ua)  # type: ignore
        browser = (parsed.get("browser") or {})
        name = (browser.get("name") or "").lower()
        if "firefox" in name:
            return "firefox"
        if "safari" in name and "chrome" not in name:
            return "webkit"
        return "chromium"
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

def _fwk_js_patch(languages: Tuple[str, ...], tz: str, ua: str) -> str:
    lang_js = json.dumps(list(languages))
    return (
        _FWK_STEALTH_TEMPLATE
        .replace("__LANG_JS__", lang_js)
        .replace("__TZ__", tz)
        .replace("__USER_AGENT__", ua)
    )


# ──────────────────────────────
# Public API
# ──────────────────────────────

async def create_context(
    playwright: Playwright,
    gate_args: Optional[Dict[str, Any]] = None,
    proxy=None,
    *,
    accept_downloads: bool = False,
    headless: bool = True,
    **extra_ctx_kwargs,
) -> Tuple[Browser, BrowserContext]:
    """Launch a browser context whose surfaces align with the UA if spoofing is requested."""
    gate_args = gate_args or {}
    spoof_ua = gate_args.get("UserAgentGate") is not None
    ua = gate_args["UserAgentGate"]["user_agent"] if spoof_ua else ""
    locale, languages = _locale_from_gate(gate_args)
    tz_id = _timezone_from_gate(gate_args)

    engine = _engine_from_ua(ua) if spoof_ua else "chromium"
    launcher = getattr(playwright, engine)
    browser: Optional[Browser] = None
    context: Optional[BrowserContext] = None

    try:
        if spoof_ua:
            base = _select_base_profile(ua)
            rand_mem = random.choice(base["mem"])
            rand_cores = random.choice(base["cores"])
            screen_w, screen_h = random.choice(base["screen"])
            webgl_vendor, webgl_renderer = (
                random.choice(base["webgl"]) if base.get("webgl") else _pick_webgl_pair(ua)
            )

            if engine == "chromium":
                from src.clienthints import extract_high_entropy_hints
                entropy = extract_high_entropy_hints(ua)
                brand, brand_v = parse_chromium_ua(ua)
                chromium_v = parse_chromium_version(ua)
                mobile_flag = "mobile" in ua.lower()
            else:
                entropy = {}
                brand = brand_v = chromium_v = ""
                mobile_flag = False
        else:
            screen_w, screen_h = 1280, 720  # Default fallback values

        launch_args = {
            "headless": headless,
            "args": ["--disable-blink-features=AutomationControlled"] if engine == "chromium" else [],
        }
        if proxy:
            launch_args["proxy"] = proxy

        browser = await launcher.launch(**launch_args)

        ctx_args = {
            "viewport": {"width": screen_w, "height": screen_h},
            "screen": {"width": screen_w, "height": screen_h},
            "accept_downloads": accept_downloads,
            **extra_ctx_kwargs,
        }

        if spoof_ua:
            ctx_args.update({
                "user_agent": ua,
                "locale": locale,
                "timezone_id": tz_id,
            })

        geo = gate_args.get("GeolocationGate", {}).get("geolocation")
        if geo is not None:
            ctx_args["geolocation"] = geo

        context = await browser.new_context(**ctx_args)

        if spoof_ua:
            # Add this mapping right after base = _select_base_profile(ua)
            conn_profile_map = {
                "desk_low": ("wifi", "3g", 5, 150, "false"),
                "desk_mid": ("wifi", "4g", 20, 80, "false"),
                "desk_high": ("ethernet", "4g", 50, 30, "false"),
                "mac_notch": ("wifi", "4g", 25, 60, "false"),
                "chrome_book": ("wifi", "3g", 10, 120, "false"),
                "mobile_high": ("cellular", "5g", 20, 100, "true"),
            }

            conn_type, eff_type, downlink, rtt, save_data = conn_profile_map.get(base["id"],
                                                                                 ("wifi", "4g", 10, 100, "false"))
            net_info_patch = _EXTRA_JS_SNIPPETS["network_info_stub.js"]
            net_info_patch = (
                net_info_patch
                .replace("__CONN_TYPE__", f'"{conn_type}"')
                .replace("__EFFECTIVE_TYPE__", f'"{eff_type}"')
                .replace("__DOWNLINK__", str(downlink))
                .replace("__RTT__", str(rtt))
                .replace("__SAVE_DATA__", save_data)
            )
            await context.add_init_script(net_info_patch)

        if spoof_ua:
            if engine == "chromium":
                await _apply_stealth(context)

                lang_js = json.dumps(list(languages))
                touch_js = (
                    "Object.defineProperty(window, 'ontouchstart', {value: null});"
                    if mobile_flag
                    else "if ('ontouchstart' in window) {} else Object.defineProperty(window, 'ontouchstart', {value: null});"
                )

                js_script = _JS_TEMPLATE.format(
                    chromium_v=chromium_v or "",
                    brand=brand,
                    brand_v=brand_v,
                    architecture=entropy.get("architecture", "x86"),
                    bitness=entropy.get("bitness", "64"),
                    wow64=str(bool(entropy.get("wow64", False))).lower(),
                    model=entropy.get("model", ""),
                    mobile=str(mobile_flag).lower(),
                    platform=entropy.get("platform", "Win32"),
                    platformVersion=entropy.get("platformVersion", "15.0"),
                    uaFullVersion=parse_chromium_full_version(ua) or chromium_v,
                )

                chromium_patch = (
                    _CHROMIUM_STEALTH_TEMPLATE
                    .replace("__LANG_JS__", lang_js)
                    .replace("__TOUCH_JS__", touch_js)
                    .replace("__BRAND__", brand)
                    .replace("__BRAND_V__", brand_v)
                    .replace("__PLATFORM__", entropy.get("platform", "Win32"))
                    .replace("__MOBILE__", str(mobile_flag).lower())
                    .replace("__ARCH__", entropy.get("architecture", "x86"))
                    .replace("__BITNESS__", entropy.get("bitness", "64"))
                    .replace("__MODEL__", entropy.get("model", ""))
                    .replace("__PLATFORM_VERSION__", entropy.get("platformVersion", "15.0"))
                    .replace("__UA_FULL_VERSION__", parse_chromium_full_version(ua) or chromium_v)
                    .replace("__WOW64__", str(bool(entropy.get("wow64", False))).lower())
                    .replace("__WEBGL_VENDOR__", webgl_vendor)
                    .replace("__WEBGL_RENDERER__", webgl_renderer)
                    .replace("__USER_AGENT__", ua)
                    .replace("__RAND_MEM__", str(rand_mem))
                    .replace("__TZ__", tz_id)
                )

                webgl_patch = (
                    _WEBGL_PATCH_TEMPLATE
                    .replace("__WEBGL_VENDOR__", webgl_vendor)
                    .replace("__WEBGL_RENDERER__", webgl_renderer)
                )

                await context.add_init_script(js_script)
                await context.add_init_script(chromium_patch)
                await context.add_init_script(_EXTRA_STEALTH)
                await context.add_init_script(webgl_patch)

            else:
                js_script = _fwk_js_patch(languages, tz_id, ua)
                await context.add_init_script(js_script)
                await context.add_init_script(_EXTRA_STEALTH)

            for body in _EXTRA_JS_SNIPPETS.values():
                await context.add_init_script(body)

        return browser, context

    except Exception as e:
        if browser:
            await browser.close()
        raise e



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
                p,
                {"UserAgentGate": {"user_agent": args.ua}},
                accept_downloads=False,  # override if you want to test downloads
            )
            page = await ctx.new_page()
            await page.goto("https://httpbin.org/headers")
            print(await page.text_content("pre"))
            await browser.close()

    asyncio.run(_demo())
