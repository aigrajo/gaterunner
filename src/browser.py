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

# ───────────────────────── data structures ──────────────────────────

@dataclass
class Config:
    """Bundle all configuration data together."""
    gates_enabled: dict = field(default_factory=dict)
    gate_args: dict = field(default_factory=dict)
    proxy: Optional[dict] = None
    engine: str = "auto"
    headless: bool = False
    interactive: bool = False
    timeout_sec: int = 30

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

# ───────────────────────── helpers (add near top of browser.py) ─────────────────────────
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
    
    # Detect browser engine from user agent if available
    engine = "chromium"  # Default
    if config.gate_args and config.gate_args.get("UserAgentGate", {}).get("user_agent"):
        ua = config.gate_args["UserAgentGate"]["user_agent"]
        low = ua.lower()
        if "firefox" in low and "seamonkey" not in low:
            engine = "firefox"
        elif "safari" in low and "chrome" not in low and "chromium" not in low:
            engine = "webkit"
    
    # Build gate configuration
    gate_config = config.gate_args.copy()
    if config.gates_enabled:
        gate_config["gates_enabled"] = config.gates_enabled
    
    # Apply spoofing using SpoofingManager
    spoofing_manager = SpoofingManager()
    await spoofing_manager.apply_spoofing(
        page=None,  # Page is created after spoofing setup
        context=context,
        gate_config=gate_config,
        engine=engine,
        url=url,
        resource_request_headers=resources.request_headers
    )

    page = await context.new_page()

    is_chromium = page.context.browser.browser_type.name == "chromium"

    if is_chromium:
        await enable_cdp_download_interceptor(
            page, Path(out_dir) / "downloads",
            resources.url_to_file, resources.response_headers, resources.stats,
        )
        dump_cdp = await attach_cdp_logger(page, out_dir)
    else:
        # no-op placeholders keep the later cleanup call happy
        dump_cdp = lambda *_, **__: None

    # network hooks
    page.on("request",  lambda r: asyncio.create_task(handle_request(r, resources)))
    page.on("response", lambda r: asyncio.create_task(
        handle_response(r, out_dir, resources)))
    downloads: list[asyncio.Task] = []
    page.on("download", lambda dl: downloads.append(
        asyncio.create_task(_save_download(dl, out_dir, resources))))

    # navigation (guarded)
    print(f"[INFO] Loading page: {url}")
    ok = await _safe_goto(page, url)
    if not ok:
        return

    # wait for downloads
    if downloads:
        await asyncio.gather(*downloads, return_exceptions=True)

    # artefacts
    os.makedirs(out_dir, exist_ok=True)
    if not page.is_closed():
        await _safe_screenshot(page, out_dir)
    save_json(os.path.join(out_dir, "http_request_headers.json"), resources.request_headers)
    save_json(os.path.join(out_dir, "http_response_headers.json"), resources.response_headers)
    save_json(os.path.join(out_dir, "cookies.json"), await context.cookies())

    # optional manual phase
    if config.interactive and not page.is_closed():
        print("[INFO] Visible window – interact freely. Close the tab to continue.")
        try:
            await page.wait_for_event("close", timeout=86_400_000)  # 24 h
        except (KeyboardInterrupt, asyncio.TimeoutError):
            pass

    print(f"Captured {len(resources.urls)} resources | "
          f"downloads={resources.stats['downloads']} warnings={resources.stats['warnings']} errors={resources.stats['errors']}")



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

    ua               = config.gate_args.get("UserAgentGate", {}).get("ua_arg", "")
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
