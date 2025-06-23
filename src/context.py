"""context.py – build a Playwright **BrowserContext** whose network layer and
JavaScript layer match the supplied User‑Agent string.

Supports three engines chosen from the UA substring:

* default / “Chrome” / “Edge” / anything else → **Chromium** (with
  *playwright‑stealth* + Client‑Hint spoof);
* “Firefox” → **Gecko** via `playwright.firefox` (no Chromium‐only patches);
* “Safari” without “Chrome” → **WebKit** via `playwright.webkit`.


"""

from __future__ import annotations

import asyncio
import json
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from timezonefinder import TimezoneFinder

from playwright.async_api import Browser, BrowserContext, Playwright

# ──────────────────────────────
# playwright‑stealth poly‑loader (Chromium only)
# ──────────────────────────────

async def _build_apply_stealth():
    """Return coroutine *apply(ctx)* for Chromium contexts; noop on others."""
    try:  # Stealth ≥ 2 – class API
        Stealth = getattr(import_module("playwright_stealth"), "Stealth")  # type: ignore[attr-defined]
        stealth_inst = Stealth(init_scripts_only=True)

        async def _apply(ctx):
            await stealth_inst.apply_stealth_async(ctx)

        return _apply
    except Exception:
        # <= 1.x function export
        for fname in ("stealth_async", "stealth"):
            try:
                func = getattr(import_module("playwright_stealth"), fname)  # type: ignore[attr-defined]
                break
            except Exception:
                func = None
        if func is None:
            async def _apply(_: BrowserContext):  # noqa: D401 – noop
                return
            return _apply

        async def _apply(ctx, _f=func):
            await _f(ctx)
        return _apply

# instantiate once
_loop = asyncio.get_event_loop() if asyncio.get_event_loop_policy().get_event_loop() else asyncio.new_event_loop()
_apply_stealth = _loop.run_until_complete(_build_apply_stealth())

# ──────────────────────────────
# Local helpers & resources
# ──────────────────────────────

from .clienthints import (  # after shim
    extract_high_entropy_hints,
    parse_chromium_full_version,
    parse_chromium_ua,
    parse_chromium_version,
)

_JS_TEMPLATE_PATH = Path(__file__).resolve().parent / "js" / "spoof_useragent.js"
_JS_TEMPLATE = _JS_TEMPLATE_PATH.read_text(encoding="utf-8")

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


def _engine_from_ua(ua: str) -> str:
    low = ua.lower()
    if "firefox" in low and "seamonkey" not in low:
        return "firefox"
    if "safari" in low and "chrome" not in low and "chromium" not in low:
        return "webkit"
    return "chromium"


def _locale_from_gate(gate_args: Dict[str, Any]) -> Tuple[str, Tuple[str, ...]]:
    raw = gate_args.get("LanguageGate", {}).get("language") if gate_args else None
    if not raw:
        return "en-US", ("en-US", "en")
    primary = raw.split(",", 1)[0].strip()
    return primary, (primary, primary.split("-", 1)[0])

_tzf = TimezoneFinder()
def _tz_from_coords(lat: float, lon: float) -> str:
    return _tzf.timezone_at(lat=lat, lng=lon) or "UTC"

def _timezone_from_gate(gate_args):
    geo_gate = gate_args.get("GeolocationGate", {})
    if "timezone_id" in geo_gate:
        return geo_gate["timezone_id"]
    if "geolocation" in geo_gate:
        lat = geo_gate["geolocation"]["latitude"]
        lon = geo_gate["geolocation"]["longitude"]
        return _tz_from_coords(lat, lon)
    return "UTC"

# ──────────────────────────────
# Public API
# ──────────────────────────────

async def create_context(
    playwright: Playwright,
    gate_args: Optional[Dict[str, Any]] = None,
) -> Tuple[Browser, BrowserContext]:
    """Return *(browser, context)* whose engine matches the UA string."""

    gate_args = gate_args or {}

    # fingerprint base -----------------------------------------------------
    ua: str = gate_args.get("UserAgentGate", {}).get("user_agent", _DEFAULT_UA)
    locale, languages = _locale_from_gate(gate_args)
    tz_id = _timezone_from_gate(gate_args)

    engine = _engine_from_ua(ua)

    # extract entropy only for Chromium – others skip Client Hints ----------
    if engine == "chromium":
        entropy = extract_high_entropy_hints(ua)
        brand, brand_v = parse_chromium_ua(ua)
        chromium_v = parse_chromium_version(ua)
    else:
        entropy = {}
        brand = brand_v = chromium_v = ""

    fp: Dict[str, Any] = {
        "ua": ua,
        "languages": languages,
        "tz": tz_id,
        "mem": 8,
        "cores": 8,
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
            webgl_vendor="Google Inc.",
            webgl_renderer="ANGLE (Intel(R) UHD Graphics 630)",
        )

    # launch ---------------------------------------------------------------
    launcher = getattr(playwright, engine)
    browser: Browser = await launcher.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled"] if engine == "chromium" else [],
    )

    ctx_args: Dict[str, Any] = {
        "user_agent": fp["ua"],
        "locale": locale,
        "timezone_id": fp["tz"],
    }
    if geo := gate_args.get("GeolocationGate", {}).get("geolocation"):
        ctx_args["geolocation"] = geo

    context: BrowserContext = await browser.new_context(**ctx_args)

    # stealth & js patches --------------------------------------------------
    if engine == "chromium":
        await _apply_stealth(context)

        # full CH spoof
        lang_js = json.dumps(list(fp["languages"]))
        js_script = _JS_TEMPLATE.format(
            chromium_v=chromium_v or "",
            brand=fp["brand"],
            brand_v=fp["brand_v"],
            architecture=fp.get("arch", "x86"),
            bitness=fp.get("bitness", "64"),
            wow64=str(bool(fp.get("wow64", False))).lower(),
            model=entropy.get("model", ""),
            mobile=str("mobile" in ua.lower()).lower(),
            platform=fp.get("platform", "Win32"),
            platformVersion=fp.get("platform_version", "15.0"),
            uaFullVersion=fp.get("ua_full_version", chromium_v),
        ) + (
            f"\nObject.defineProperty(navigator, 'languages', {{ get: () => {lang_js} }});"
        )
        await context.add_init_script(js_script)
    else:
        # minimal patch: align languages & timezone for non‑Chromium
        lang_js = json.dumps(list(fp["languages"]))
        js_script = (
            f"/* basic‑fp */\n"
            f"Object.defineProperty(navigator, 'languages', {{ get: () => {lang_js} }});\n"
            f"Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {{ value: () => {{ timeZone: '{fp['tz']}' }} }});\n"
            f"Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {fp['mem']} }});\n"
            f"Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {fp['cores']} }});\n"
        )
        await context.add_init_script(js_script)

    return browser, context

# ──────────────── quick test ─────────────────
if __name__ == "__main__":

    async def _demo(ua: str):
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser, ctx = await create_context(p, gate_args={"UserAgentGate": {"user_agent": ua}})
            page = await ctx.new_page()
            await page.goto("https://google.com", wait_until="commit")
            print(await page.text_content("pre"))
            await browser.close()

    asyncio.run(_demo("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15"))
