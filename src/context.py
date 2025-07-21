from src.clienthints import parse_chromium_ua, parse_chromium_version, parse_chromium_full_version

"""
context.py – create a Playwright **BrowserContext** with a JavaScript and
network fingerprint that consistently matches the supplied User‑Agent string.

Uses the unified spoofing system to orchestrate both HTTP-level and browser-level
fingerprinting through the gate architecture.
"""

import asyncio
import json
import random
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from functools import lru_cache
from playwright.async_api import Browser, BrowserContext, Playwright

from src.spoof_manager import SpoofingManager
from src.debug import debug_print

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

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

_BASE_PROFILES_PATH = Path("src/data/base_profiles.json")

@lru_cache(maxsize=1)
def _load_base_profiles() -> List[Dict[str, Any]]:
    """Return the profiles stored in base_profiles.json.

    The lru_cache decorator keeps the parsed data
    in memory, so repeated calls hit the cache
    instead of the file system.
    """
    with _BASE_PROFILES_PATH.open(encoding="utf-8") as f:
        return json.load(f)

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
    _BASE_PROFILES = _load_base_profiles()
    candidates = [p for p in _BASE_PROFILES if os_family in p["os"]]
    if not candidates:
        candidates = _BASE_PROFILES  # fallback – shouldn't happen
    return random.choice(candidates)

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
    """Launch a browser context with unified spoofing applied via the gate system."""
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
                random.choice(base["webgl"]) if base.get("webgl") else ("Intel", "Intel(R) HD Graphics 530")
            )
            
            # Map base profile to connection profile
            conn_profile_map = {
                "desk_low": "desk_low",
                "desk_mid": "desk_mid", 
                "desk_high": "desk_high",
                "mac_notch": "mac_notch",
                "chrome_book": "chrome_book",
                "mobile_high": "mobile_high",
            }
            connection_profile = conn_profile_map.get(base["id"], "wifi")
        else:
            screen_w, screen_h = 1280, 720  # Default fallback values
            rand_mem = 8
            webgl_vendor, webgl_renderer = "Intel", "Intel(R) HD Graphics 530"
            connection_profile = "wifi"

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
            # Apply unified spoofing using the gate system
            spoofing_manager = SpoofingManager()
            
            # Enhanced gate configuration with additional context
            enhanced_gate_args = gate_args.copy()
            
            # Add network configuration if not present
            if "NetworkGate" not in enhanced_gate_args:
                enhanced_gate_args["NetworkGate"] = {"connection_profile": connection_profile}
            
            # Add WebGL configuration - always ensure WebGLGate has proper config
            if "WebGLGate" not in enhanced_gate_args:
                enhanced_gate_args["WebGLGate"] = {
                    "webgl_vendor": webgl_vendor,
                    "webgl_renderer": webgl_renderer,
                    "user_agent": ua
                }
            else:
                # Ensure user_agent is passed for auto-detection if vendor/renderer not explicit
                webgl_config = enhanced_gate_args["WebGLGate"]
                if "user_agent" not in webgl_config:
                    webgl_config["user_agent"] = ua
                # Use context-detected values as fallbacks
                if "webgl_vendor" not in webgl_config:
                    webgl_config["webgl_vendor"] = webgl_vendor
                if "webgl_renderer" not in webgl_config:
                    webgl_config["webgl_renderer"] = webgl_renderer
            
            # Add timezone to UserAgentGate for template variables
            if "UserAgentGate" in enhanced_gate_args:
                enhanced_gate_args["UserAgentGate"]["timezone_id"] = tz_id
                enhanced_gate_args["UserAgentGate"]["rand_mem"] = rand_mem
                # Pass language information to UserAgentGate for template vars
                if "LanguageGate" in enhanced_gate_args:
                    lang_config = enhanced_gate_args["LanguageGate"]
                    enhanced_gate_args["UserAgentGate"]["accept_language"] = (
                        lang_config.get("accept_language") or lang_config.get("language")
                    )
            
            # Add timezone and user agent to LanguageGate for template variables
            if "LanguageGate" in enhanced_gate_args:
                enhanced_gate_args["LanguageGate"]["timezone_id"] = tz_id
                enhanced_gate_args["LanguageGate"]["user_agent"] = ua
            
            # Debug: Show final gate configuration
            debug_print(f"[DEBUG] Enhanced gate config: {enhanced_gate_args}")
            
            # Apply unified spoofing (no page yet, will be set later)
            await spoofing_manager.apply_spoofing(
                page=None,
                context=context,
                gate_config=enhanced_gate_args,
                engine=engine,
                url=None,
                resource_request_headers=None
            )
        
            # Ensure gate_args retains finalized WebGL config for later reuse
            gate_args["WebGLGate"] = enhanced_gate_args["WebGLGate"]
        
        # Apply playwright-stealth if available (Chromium only)
        if engine == "chromium":
            await _apply_stealth(context)

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
