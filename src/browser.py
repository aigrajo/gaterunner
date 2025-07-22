"""
browser.py
==========

Drives Playwright, CamouFox or Patchright, captures every redirect hop,
saves artefacts, and tallies stats: downloads / warnings / errors.
"""
import asyncio, os, hashlib
from contextlib import suppress
from pathlib import Path
from urllib.parse import urlparse
from dataclasses import dataclass, field
from typing import Optional

from playwright._impl._errors import TargetClosedError
from playwright.async_api import async_playwright as async_pw, Error

from .cdp_logger import attach_cdp_logger
from .debug import debug_print

# ───────────────────────── data structures ──────────────────────────

@dataclass
class Config:
    """Centralized configuration for all gaterunner functionality."""
    
    # ─── Application Configuration ───
    engine: str = "auto"
    headless: bool = False
    interactive: bool = False
    timeout_sec: int = 30
    verbose: bool = False
    output_dir: str = "./data"
    plain_progress: bool = False
    workers: Optional[int] = None
    
    # ─── Network Configuration ───
    proxy: Optional[dict] = None
    
    # ─── Gate Configuration (Spoofing Settings) ───
    gates_enabled: dict = field(default_factory=dict)
    gate_args: dict = field(default_factory=dict)
    
    # ─── Detected Configuration (Set during runtime) ───
    detected_engine: Optional[str] = field(default=None, init=False)
    
    @classmethod
    def from_args(cls, args) -> 'Config':
        """Create a Config instance from command line arguments."""
        config = cls()
        
        # Application settings
        config.engine = args.engine
        config.interactive = args.headful
        config.timeout_sec = int(args.timeout)
        config.verbose = args.verbose
        config.output_dir = args.output_dir
        config.plain_progress = args.plain_progress
        config.workers = args.workers
        
        # Network settings
        if args.proxy and _is_valid_proxy(args.proxy):
            config.proxy = {"server": args.proxy}
        
        # Gate configuration
        config._configure_geolocation_gate(args)
        config._configure_language_gate(args)
        config._configure_useragent_gate(args)
        
        return config
    
    def _configure_geolocation_gate(self, args):
        """Configure GeolocationGate and related gates."""
        from src.gates.geolocation import COUNTRY_GEO, jitter_country_location
        
        if args.country:
            cc = args.country.upper()
            if cc not in COUNTRY_GEO:
                raise ValueError(f"Invalid country code: {cc}")
            
            self.gates_enabled["GeolocationGate"] = True
            self.gate_args["GeolocationGate"] = {"geolocation": jitter_country_location(cc)}
            
            # Enable TimezoneGate with country code for dynamic timezone selection
            self.gates_enabled["TimezoneGate"] = True
            self.gate_args["TimezoneGate"] = {"country": cc}
    
    def _configure_language_gate(self, args):
        """Configure LanguageGate."""
        if args.lang:
            if not _is_valid_lang(args.lang):
                raise ValueError(f"Invalid language: {args.lang}")
            
            self.gates_enabled["LanguageGate"] = True
            self.gate_args["LanguageGate"] = {"language": args.lang}
    
    def _configure_useragent_gate(self, args):
        """Configure UserAgentGate."""
        from src.gates.useragent import choose_ua
        
        if args.ua_full:
            ua_value = args.ua_full.strip()
            self.gates_enabled["UserAgentGate"] = True
            self.gate_args["UserAgentGate"] = {
                "user_agent": ua_value,
                "ua_arg": ua_value,  # used later for engine selection
            }
        elif args.ua:
            resolved_ua = choose_ua(args.ua)
            self.gates_enabled["UserAgentGate"] = True
            self.gate_args["UserAgentGate"] = {
                "user_agent": resolved_ua,
                "ua_arg": args.ua,
            }
    
    def get_gate_config(self) -> dict:
        """Build complete gate configuration for SpoofingManager."""
        gate_config = self.gate_args.copy()
        
        if self.gates_enabled:
            gate_config["gates_enabled"] = self.gates_enabled
        
        # Add browser engine choice for patch control
        gate_config["browser_engine"] = self.engine
        
        return gate_config
    
    def detect_engine_from_ua(self) -> str:
        """Detect browser engine from user agent if available."""
        if not self.detected_engine:
            if self.gate_args and self.gate_args.get("UserAgentGate", {}).get("user_agent"):
                from src.clienthints import detect_engine_from_ua
                ua = self.gate_args["UserAgentGate"]["user_agent"]
                self.detected_engine = detect_engine_from_ua(ua)
            else:
                self.detected_engine = "chromium"  # Default
        
        return self.detected_engine
    
    def get_ua_for_engine_selection(self) -> str:
        """Get user agent string for engine selection purposes."""
        return self.gate_args.get("UserAgentGate", {}).get("ua_arg", "")


# ────────────── optional engines ──────────────
try:
    from camoufox.async_api import AsyncCamoufox          # type: ignore
    _HAS_CAMOUFOX = True
except ImportError:
    _HAS_CAMOUFOX = False

try:
    from patchright.async_api import async_playwright as async_patchright  # type: ignore
    _HAS_PATCHRIGHT = True
except ImportError:
    _HAS_PATCHRIGHT = False
    async_patchright = None  # type: ignore

from .context import create_context
from .spoof_manager import SpoofingManager
from .resources import (
    ResourceData,
    handle_request,
    handle_response,
    save_json,
    save_screenshot,
    _fname_from_url,
    enable_cdp_download_interceptor, _make_slug
)

from playwright._impl._errors import Error as PWError, TargetClosedError   # keeps old imports working

async def _safe_goto(page, url: str, *, timeout: int = 40_000) -> bool:
    """Navigate and swallow frame-detached / aborted errors.

    Returns True on success, False when the page aborted (usually because
    the CDP download interceptor detached the frame). Other errors still log.
    """
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        return True
    except PWError as exc:
        if "net::ERR_ABORTED" in str(exc):
            print(f"[ABORT] {url} – frame detached after download intercept")
        else:
            print(f"[ERROR] Failed to load {url}: {exc}")
        # 🔽 make sure the tab is gone, swallow any error
        with suppress(Exception):
            await page.close()
        return False


async def _safe_screenshot(page, out_dir: str) -> None:
    """Take a screenshot only if the tab is still alive."""
    try:
        await page.screenshot(path=f"{out_dir}/screenshot.png", full_page=True)
    except TargetClosedError:
        print("[INFO] tab closed before screenshot – skipped")
    except Exception as exc:
        print(f"[WARN] screenshot failed: {exc}")



async def _save_download(dl, out_dir: str, resources: ResourceData):
    """Save a Playwright Download, avoiding duplicates from the CDP stream hook."""
    name = dl.suggested_filename or _fname_from_url(dl.url, "")
    dst  = Path(out_dir) / "downloads" / name
    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists():                       # already written by CDP interceptor
        print(f"[SKIP] {dst.name} already written by CDP hook")
        return

    try:
        await dl.save_as(dst)
        resources.stats["downloads"] += 1
        print(f"[DOWNLOAD] Saved: {dst.name}")
    except Exception as exc:
        resources.stats["errors"] += 1
        print(f"[WARN] Failed to save {name}: {type(exc).__name__}: {exc}")


# ───────────────────────── page grabber ─────────────────────────────
async def _grab(                     # noqa: C901 – long but linear
    browser,
    context,
    url: str,
    out_dir: str,
    resources: ResourceData,
    config: Config,
    *,
    pause_ms: int,
    max_scrolls: int | None,
):
    """Navigate, collect artefacts, then optionally pause for user inspection."""
    
    # Build gate configuration using centralized method
    gate_config = config.get_gate_config()
    debug_print(f"[DEBUG] Page-level setup for URL: {url}")
    
    # Create page (spoofing was already applied during context creation)
    page = await context.new_page()

    # Set up page-specific handlers (like worker synchronization)
    spoofing_manager = SpoofingManager()
    await spoofing_manager.setup_page_handlers(page, context, gate_config)

    is_chromium = page.context.browser.browser_type.name == "chromium"

    if is_chromium:
        await enable_cdp_download_interceptor(
            page, Path(out_dir) / "downloads",
            resources,
        )
        dump_cdp = await attach_cdp_logger(page, out_dir)
    else:
        # no-op placeholders keep the later cleanup call happy
        dump_cdp = lambda *_, **__: None

    # network hooks
    page.on("request",  lambda r: asyncio.create_task(handle_request(r, resources)))
    page.on("response", lambda r: asyncio.create_task(
        handle_response(r, out_dir, resources)))
    
    # Capture request headers for debugging (was previously done in duplicate apply_spoofing call)
    async def capture_request_headers(route, request):
        resources.request_headers[request.url] = {
            "method": request.method,
            **dict(request.headers)
        }
        await route.continue_()
    
    await page.route("**/*", capture_request_headers)
    downloads: list[asyncio.Task] = []
    page.on("download", lambda dl: downloads.append(
        asyncio.create_task(_save_download(dl, out_dir, resources))))

    # navigation (guarded)
    print(f"[INFO] Loading page: {url}")
    ok = await _safe_goto(page, url)
    
    # wait for downloads regardless of page load success
    if downloads:
        await asyncio.gather(*downloads, return_exceptions=True)

    # artefacts - always save metadata even if page aborted
    os.makedirs(out_dir, exist_ok=True)
    if not page.is_closed():
        await _safe_screenshot(page, out_dir)
    save_json(os.path.join(out_dir, "http_request_headers.json"), resources.request_headers)
    save_json(os.path.join(out_dir, "http_response_headers.json"), resources.response_headers)
    
    # Save cookies with error handling in case context is closed
    try:
        cookies = await context.cookies()
    except Exception as e:
        print(f"[WARN] Could not collect cookies: {e}")
        cookies = []
    save_json(os.path.join(out_dir, "cookies.json"), cookies)
    
    # Comprehensive stats message for all sites
    print(f"[STATS] Captured {len(resources.urls)} resources | "
          f"requests={len(resources.request_headers)} responses={len(resources.response_headers)} files={len(resources.url_to_file)} | "
          f"downloads={resources.stats['downloads']} warnings={resources.stats['warnings']} errors={resources.stats['errors']}")
    
    # Early return only after metadata is saved
    if not ok:
        print(f"[INFO] Page aborted after download intercept: {url}")
        return

    # optional manual phase
    if config.interactive and not page.is_closed():
        print("[INFO] Visible window – interact freely. Close the tab to continue.")
        try:
            await page.wait_for_event("close", timeout=86_400_000)  # 24 h
        except (KeyboardInterrupt, asyncio.TimeoutError):
            pass



# ───────────────────────── public API ──────────────────────────────
async def save_page(
    url: str,
    out_dir: str,
    resources: ResourceData,
    config: Config,
):
    """Decide which engine to use, then delegate to *_grab*."""

    # ----- output dir slug -----
    parsed = urlparse(url)
    netloc = parsed.netloc.replace(":", "_")
    path   = parsed.path.strip("/").replace("/", "_") or "root"
    path = parsed.path.strip("/").replace("/", "_") or "root"
    slug = _make_slug(netloc, path)
    out_dir = os.path.join(os.path.dirname(out_dir), f"saved_{slug}")

    pause_ms, max_scrolls = 150, config.gate_args.get("max_scrolls")

    async def _run(br, ctx):
        try:
            await _grab(
                br, ctx, url, out_dir,
                resources, config,
                pause_ms=pause_ms, max_scrolls=max_scrolls,
            )
        finally:
            with suppress(Exception):
                await br.close()

    ua               = config.get_ua_for_engine_selection()
    want_camoufox    = config.engine == "camoufox"
    want_patchright  = config.engine == "patchright"
    force_playwright = config.engine == "playwright"

    # ---------- CamouFox branch ----------
    orig_display = os.environ.get("DISPLAY")          # preserve outer Xvfb
    if (_HAS_CAMOUFOX and not force_playwright and
            (want_camoufox or ("firefox" in ua.lower() and not want_patchright))):
        try:
            print("[INFO] Launching CamouFox")
            camou_headless = True if not config.interactive else False
            async with AsyncCamoufox(headless=camou_headless,
                                     proxy=config.proxy, geoip=True) as br:
                ctx = await br.new_context(accept_downloads=True)
                await asyncio.wait_for(_run(br, ctx), timeout=config.timeout_sec)
                return
        except Exception as e:
            print(f"[WARN] CamouFox failed: {e}")
            # restore outer X display before bailing / retrying
            if orig_display:
                os.environ["DISPLAY"] = orig_display

            # explicit --engine camoufox → do NOT fall back; bubble up
            if config.engine != "auto":
                raise

            # auto mode only: try next engine
            print("Falling back.")

    # ---------- Patchright branch ----------
    if _HAS_PATCHRIGHT and want_patchright and not force_playwright:
        try:
            print("[INFO] Launching Patchright")
            async with async_patchright() as p:
                br, ctx = await create_context(
                    p, config.gate_args, proxy=config.proxy,
                    accept_downloads=True, headless=config.headless
                )
                await asyncio.wait_for(_run(br, ctx), timeout=config.timeout_sec)
                return
        except Exception as e:
            print(f"[WARN] Patchright failed: {e}")
            raise

    # ---------- Stock Playwright ----------
    async with async_pw() as p:
        br, ctx = await create_context(
            p, config.gate_args, proxy=config.proxy,
            accept_downloads=True, headless=config.headless
        )
        await asyncio.wait_for(_run(br, ctx), timeout=config.timeout_sec)

# ─── Helper functions ───

def _is_valid_proxy(proxy: str) -> bool:
    """Validate proxy format."""
    import re
    return re.fullmatch(r"(socks5|http)://.+:\d{2,5}", proxy) is not None


def _is_valid_lang(lang: str) -> bool:
    """Validate language code format."""
    import re
    return re.fullmatch(r"[a-z]{2,3}(-[A-Z]{2})?$", lang) is not None
