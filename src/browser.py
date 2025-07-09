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

from playwright._impl._errors import TargetClosedError
from playwright.async_api import async_playwright as async_pw, Error

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
from .gaterunner import run_gates
from .resources import (
    handle_request,
    handle_response,
    save_json,
    save_screenshot,
    _fname_from_url,
)

# ───────────────────────── download helper ──────────────────────────
async def _save_download(dl, out_dir: str, stats: dict):
    name = dl.suggested_filename or _fname_from_url(dl.url, "")
    dst = Path(out_dir) / "downloads" / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        await dl.save_as(dst)
        stats["downloads"] += 1
        print(f"[DOWNLOAD] Saved: {dst.name}")
    except Exception as e:
        stats["errors"] += 1
        print(f"[WARN] Failed to save {name}: {type(e).__name__}: {e}")

# ───────────────────────── page grabber ─────────────────────────────
async def _grab(                     # noqa: C901 – long but linear
    browser,
    context,
    url: str,
    out_dir: str,
    res_urls: set[str],
    req_hdrs: dict,
    resp_hdrs: dict,
    url_map: dict,
    stats: dict,
    *,
    pause_ms: int,
    max_scrolls: int | None,
    gates_enabled,
    gate_args,
    interactive: bool,
):
    """Navigate, collect artefacts, then optionally pause for user inspection."""
    await run_gates(
        None, context,
        gates_enabled=gates_enabled, gate_args=gate_args,
        url=url, resource_request_headers=req_hdrs,
    )

    page = await context.new_page()

    # network hooks
    page.on("request",  lambda r: asyncio.create_task(handle_request(r, res_urls)))
    page.on("response", lambda r: asyncio.create_task(
        handle_response(r, out_dir, url_map, resp_hdrs, stats)))
    downloads: list[asyncio.Task] = []
    page.on("download", lambda dl: downloads.append(
        asyncio.create_task(_save_download(dl, out_dir, stats))))

    # navigation
    print(f"[INFO] Loading page: {url}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=0)
    except Error as exc:
        if ("Download is starting" not in str(exc)) and ("net::ERR_ABORTED" not in str(exc)):
            print(f"[ERROR] Failed to load {url}: {exc}")
            stats["errors"] += 1

    # wait for downloads
    if downloads:
        await asyncio.gather(*downloads, return_exceptions=True)

    # artefacts
    os.makedirs(out_dir, exist_ok=True)
    if not page.is_closed():
        await save_screenshot(page, out_dir)
    save_json(os.path.join(out_dir, "http_request_headers.json"), req_hdrs)
    save_json(os.path.join(out_dir, "http_response_headers.json"), resp_hdrs)
    save_json(os.path.join(out_dir, "cookies.json"), await context.cookies())

    # optional manual phase
    if interactive and not page.is_closed():
        print("[INFO] Visible window – interact freely. Close the tab to continue.")
        try:
            await page.wait_for_event("close", timeout=86400000)  # up to 24 h
        except (KeyboardInterrupt, asyncio.TimeoutError):
            pass

    print(f"Captured {len(res_urls)} resources | "
          f"downloads={stats['downloads']} warnings={stats['warnings']} errors={stats['errors']}")

    # ← **browser.close() removed** – one close per browser instance happens in _run


# ───────────────────────── public API ──────────────────────────────
async def save_page(
    url: str,
    out_dir: str,
    *,
    gates_enabled: dict | None = None,
    gate_args: dict | None = None,
    proxy: dict | None = None,
    engine: str = "auto",          # auto | playwright | camoufox | patchright
    launch_headless: bool = False, # Playwright launch flag (always False for realism)
    interactive: bool = False,     # True ⇢ real window, False ⇢ Xvfb-hidden
    timeout_sec: int = 30,
):
    """Decide which engine to use, then delegate to *_grab*."""
    gates_enabled = gates_enabled or {}
    gate_args     = gate_args or {}

    # ----- output dir slug -----
    parsed = urlparse(url)
    netloc = parsed.netloc.replace(":", "_")
    path   = parsed.path.strip("/").replace("/", "_") or "root"
    slug   = f"{netloc}_{path}"
    short  = hashlib.md5(url.encode()).hexdigest()[:6]
    out_dir = os.path.join(os.path.dirname(out_dir), f"saved_{slug}_{short}")

    res_urls: set[str] = set()
    stats = {"warnings": 0, "errors": 0, "downloads": 0}
    req_hdrs, resp_hdrs, url_map = {}, {}, {}
    pause_ms, max_scrolls = 150, gate_args.get("max_scrolls")

    async def _run(br, ctx):
        try:
            await _grab(
                br, ctx, url, out_dir,
                res_urls, req_hdrs, resp_hdrs, url_map, stats,
                pause_ms=pause_ms, max_scrolls=max_scrolls,
                gates_enabled=gates_enabled, gate_args=gate_args,
                interactive=interactive
            )
        finally:
            with suppress(Exception):
                await br.close()

    ua               = gate_args.get("UserAgentGate", {}).get("ua_arg", "")
    want_camoufox    = engine == "camoufox"
    want_patchright  = engine == "patchright"
    force_playwright = engine == "playwright"

    # ---------- CamouFox branch ----------
    orig_display = os.environ.get("DISPLAY")          # preserve outer Xvfb
    if (_HAS_CAMOUFOX and not force_playwright and
            (want_camoufox or ("firefox" in ua.lower() and not want_patchright))):
        try:
            print("[INFO] Launching CamouFox")
            camou_headless = True if not interactive else False
            async with AsyncCamoufox(headless=camou_headless,
                                     proxy=proxy, geoip=True) as br:
                ctx = await br.new_context(accept_downloads=True)
                await asyncio.wait_for(_run(br, ctx), timeout=timeout_sec)
                return
        except Exception as e:
            print(f"[WARN] CamouFox failed: {e}. Falling back.")
            if orig_display:
                os.environ["DISPLAY"] = orig_display  # restore for fallback

    # ---------- Patchright branch ----------
    if _HAS_PATCHRIGHT and want_patchright and not force_playwright:
        try:
            print("[INFO] Launching Patchright")
            async with async_patchright() as p:
                br, ctx = await create_context(
                    p, gate_args, proxy=proxy,
                    accept_downloads=True, headless=launch_headless
                )
                await asyncio.wait_for(_run(br, ctx), timeout=timeout_sec)
                return
        except Exception as e:
            print(f"[WARN] Patchright failed: {e}. Falling back.")

    # ---------- Stock Playwright ----------
    async with async_pw() as p:
        br, ctx = await create_context(
            p, gate_args, proxy=proxy,
            accept_downloads=True, headless=launch_headless
        )
        await asyncio.wait_for(_run(br, ctx), timeout=timeout_sec)
