"""context.py – create a Playwright `BrowserContext` that looks like a real
browser session.

* Keeps every spoofed value (UA, locale, timezone, client hints …) coherent
  between HTTP headers and JavaScript land.
"""

from __future__ import annotations

import asyncio
import json
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from playwright.async_api import Browser, BrowserContext, Playwright

# ──────────────────────────────
# playwright‑stealth compatibility shim
# ──────────────────────────────

async def _build_apply_stealth():
    """Return a coroutine `apply(ctx)` that patches *ctx* with stealth."""
    try:  # Preferred ≥ 2.0: Stealth class
        mod = import_module("playwright_stealth")
        Stealth = getattr(mod, "Stealth")  # type: ignore[attr-defined]
        stealth_inst = Stealth(init_scripts_only=True)

        async def _apply(ctx):  # noqa: D401 – simple wrapper
            await stealth_inst.apply_stealth_async(ctx)

        return _apply
    except Exception:
        # Legacy 1.x – function export (`stealth_async` or `stealth`)
        for fname in ("stealth_async", "stealth"):
            try:
                func = getattr(import_module("playwright_stealth"), fname)  # type: ignore[attr-defined]
            except Exception:
                try:
                    func = getattr(import_module("playwright_stealth.stealth"), fname)  # type: ignore[attr-defined]
                except Exception:
                    func = None
            if func is not None:
                async def _apply(ctx, _f=func):  # bind current *func*
                    await _f(ctx)
                return _apply
        raise ImportError("No compatible playwright‑stealth export found")

# Build the shim once at import time – handle missing loop on Py 3.9
try:
    _loop = asyncio.get_event_loop()
except RuntimeError:  # no running loop yet → make one
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
_apply_stealth = _loop.run_until_complete(_build_apply_stealth())

# ──────────────────────────────
# Project‑local imports
# ──────────────────────────────

from .clienthints import (  # noqa: E402  – after shim
    extract_high_entropy_hints,
    parse_chromium_full_version,
    parse_chromium_ua,
    parse_chromium_version,
)

# ──────────────────────────────
# Resources & defaults
# ──────────────────────────────

_JS_TEMPLATE_PATH = Path(__file__).resolve().parent / "js" / "spoof_useragent.js"
_JS_TEMPLATE: str = _JS_TEMPLATE_PATH.read_text(encoding="utf-8")

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# ──────────────────────────────
# Helper functions
# ──────────────────────────────

def _locale_from_gate(gate_args: Dict[str, Any]) -> Tuple[str, Tuple[str, ...]]:
    raw: Optional[str] = gate_args.get("LanguageGate", {}).get("accept_language")
    if not raw:
        return "en-US", ("en-US", "en")
    primary = raw.split(",", 1)[0].strip()
    return primary, (primary, primary.split("-", 1)[0])


def _timezone_from_gate(gate_args: Dict[str, Any]) -> str:
    return gate_args.get("GeolocationGate", {}).get("timezone_id", "UTC")

# ──────────────────────────────
# Public API
# ──────────────────────────────

async def create_context(
    playwright: Playwright,
    gate_args: Optional[Dict[str, Any]] = None,
) -> Tuple[Browser, BrowserContext]:
    """Return *(browser, context)* with aligned spoofing layers."""

    gate_args = gate_args or {}

    # 1. Build fingerprint --------------------------------------------------
    ua: str = gate_args.get("UserAgentGate", {}).get("user_agent", _DEFAULT_UA)
    locale, languages = _locale_from_gate(gate_args)
    tz_id = _timezone_from_gate(gate_args)

    entropy = extract_high_entropy_hints(ua)
    brand, brand_v = parse_chromium_ua(ua)
    chromium_v = parse_chromium_version(ua)

    fp: Dict[str, Any] = {
        "ua": ua,
        "brand": brand,
        "brand_v": brand_v,
        "ua_full_version": parse_chromium_full_version(ua) or chromium_v,
        "languages": languages,
        "tz": tz_id,
        "platform": entropy.get("platform", "Win32"),
        "platform_version": entropy.get("platformVersion", "15.0"),
        "arch": entropy.get("architecture", "x86"),
        "bitness": entropy.get("bitness", "64"),
        "wow64": entropy.get("wow64", False),
        "mem": 8,
        "cores": 8,
        "webgl_vendor": "Google Inc.",
        "webgl_renderer": "ANGLE (Intel(R) UHD Graphics 630)",
    }

    # 2. Launch browser -----------------------------------------------------
    browser: Browser = await playwright.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )

    ctx_args: Dict[str, Any] = {
        "user_agent": fp["ua"],
        "locale": locale,
        "timezone_id": fp["tz"],
    }
    geo = gate_args.get("GeolocationGate", {}).get("geolocation")
    if geo is not None:
        ctx_args["geolocation"] = geo

    context: BrowserContext = await browser.new_context(**ctx_args)

    # 3. Stealth patches ----------------------------------------------------
    await _apply_stealth(context)

    # 4. Inject fingerprint‑specific JS -------------------------------------
    lang_js = json.dumps(list(fp["languages"]))
    js_script = _JS_TEMPLATE.format(
        chromium_v=chromium_v or "",
        brand=fp["brand"],
        brand_v=fp["brand_v"],
        architecture=fp["arch"],
        bitness=fp["bitness"],
        wow64=str(bool(fp["wow64"])).lower(),
        model=entropy.get("model", ""),
        mobile=str("mobile" in ua.lower()).lower(),
        platform=fp["platform"],
        platformVersion=fp["platform_version"],
        uaFullVersion=fp["ua_full_version"],
    ) + (
        f"\n/* fp‑patch */\n"
        f"Object.defineProperty(navigator, 'languages', {{ get: () => {lang_js} }});\n"
        f"Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {{ value: () => {{ timeZone: '{fp['tz']}' }} }});\n"
        f"Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {fp['mem']} }});\n"
        f"Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {fp['cores']} }});\n"
    )

    await context.add_init_script(js_script)

    return browser, context

# ──────────────────────────────
# Quick manual test –  `python -m src.context`
# ──────────────────────────────

if __name__ == "__main__":

    async def _demo() -> None:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser, ctx = await create_context(p, gate_args={})
            page = await ctx.new_page()
            await page.goto("https://google.com", wait_until="networkidle")
            print("navigator.webdriver:", await page.evaluate("navigator.webdriver"))
            await browser.close()

    asyncio.run(_demo())
