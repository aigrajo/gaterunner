"""
browser.py
==========

Drives Playwright *or* CamouFox, captures every redirect hop,
saves final downloads, and tallies stats: downloads / warnings / errors.
"""

from __future__ import annotations
import asyncio, os
import hashlib
from contextlib import suppress
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Error

try:
    from camoufox.async_api import AsyncCamoufox       # type: ignore
    _HAS_CAMOUFOX = True
except ImportError:
    _HAS_CAMOUFOX = False

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
    await dl.save_as(dst)
    stats["downloads"] += 1
    print(f"[DOWNLOAD] Saved: {dst.name}")

# ───────────────────────── page grabber ─────────────────────────────

async def _grab(
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
):
    # gates (UA spoof etc.)
    await run_gates(
        None, context,
        gates_enabled=gates_enabled, gate_args=gate_args,
        url=url, resource_request_headers=req_hdrs,
    )

    page = await context.new_page()

    # network hooks
    page.on("request", lambda r: asyncio.create_task(handle_request(r, res_urls)))
    page.on("response", lambda r: asyncio.create_task(
        handle_response(r, out_dir, url_map, resp_hdrs, stats)))
    downloads: list[asyncio.Task] = []
    page.on("download", lambda dl: downloads.append(
        asyncio.create_task(_save_download(dl, out_dir, stats))))

    # navigation
    print(f"[INFO] Loading page: {url}")
    try:
        await page.goto(url.strip(), wait_until="domcontentloaded", timeout=0)
    except Error as exc:
        msg = str(exc)
        if ("Download is starting" in msg) or ("net::ERR_ABORTED" in msg):
            print("[INFO] Navigation became a download; DOM skipped")
        else:
            print(f"[ERROR] Failed to load {url}: {exc}")
            stats["errors"] += 1

    if downloads:
        results = await asyncio.gather(*downloads, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                print(f"[WARN] Download task failed: {type(result).__name__}: {result}")

    # scroll to bottom (if still open)
    if not page.is_closed():
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        try:
            await page.wait_for_load_state("load", timeout=10000)
        except Error:
            print("[WARN] Timeout waiting for load state. Proceeding anyway.")

    # artefacts
    os.makedirs(out_dir, exist_ok=True)
    if not page.is_closed():
        await save_screenshot(page, out_dir)

    save_json(os.path.join(out_dir, "http_request_headers.json"), req_hdrs)
    save_json(os.path.join(out_dir, "http_response_headers.json"), resp_hdrs)
    save_json(os.path.join(out_dir, "cookies.json"), await context.cookies())

    if not page.is_closed():
        with suppress(Error):
            html = await page.content()
            if html:
                from .html import save_html_files
                save_html_files(out_dir, html, url_map)

    print(f"Captured {len(res_urls)} resources")
    print(f"downloads={stats['downloads']} warnings={stats['warnings']} errors={stats['errors']}")

    await browser.close()

# ───────────────────────── public API ──────────────────────────────

async def save_page(
    url: str,
    out_dir: str,
    *,
    gates_enabled: dict | None = None,
    gate_args: dict | None = None,
    proxy: dict | None = None,
    engine: str = "auto"
):
    gates_enabled = gates_enabled or {}
    gate_args = gate_args or {}


    parsed = urlparse(url)
    netloc = parsed.netloc.replace(":", "_")
    path = parsed.path.strip("/").replace("/", "_") or "root"
    slug = f"{netloc}_{path}"
    short_hash = hashlib.md5(url.encode()).hexdigest()[:6]
    out_dir = os.path.join(os.path.dirname(out_dir), f"saved_{slug}_{short_hash}")

    pause_ms = gate_args.get("scroll_pause_ms", 150)
    max_scrolls = gate_args.get("max_scrolls")

    res_urls: set[str] = set()
    req_hdrs, resp_hdrs, url_map = {}, {}, {}
    stats = {"warnings": 0, "errors": 0, "downloads": 0}

    async def _run(br, ctx):
        await _grab(
            br, ctx, url, out_dir,
            res_urls, req_hdrs, resp_hdrs, url_map, stats,
            pause_ms=pause_ms, max_scrolls=max_scrolls,
            gates_enabled=gates_enabled, gate_args=gate_args,
        )

    # choose engine (CamouFox vs stock)
    ua = gate_args.get("UserAgentGate", {}).get("user_agent", "")
    want_camoufox = engine == "camoufox"
    force_playwright = engine == "playwright"
    use_camoufox = _HAS_CAMOUFOX and not force_playwright and (
            want_camoufox or "firefox" in ua.lower()
    )

    if use_camoufox and "firefox" in ua.lower() and not want_camoufox:
        print("[INFO] 'firefox' detected in UA – switching to CamouFox engine.")
        if any(gates_enabled.get(g) for g in ("UserAgentGate", "GeolocationGate", "LanguageGate")):
            print("[WARN] CamouFox overrides most spoofing gates – UA/geo/lang spoofing may not apply. Use --engine to switch to Playwright's engine")

    if use_camoufox:
        try:
            print("[INFO] Launching CamouFox browser")
            async with AsyncCamoufox(headless=True, proxy=proxy, geoip=True) as br:
                try:
                    ctx = await br.new_context(accept_downloads=True)
                except TypeError:
                    print("[WARN] CamouFox lacks accept_downloads – downloads must be saved via response body")
                    ctx = await br.new_context()
                await _run(br, ctx)
                return
        except Exception as e:
            print(f"[WARN] CamouFox failed: {e}. Falling back to stock.")

    async with async_playwright() as p:
        br, ctx = await create_context(p, gate_args, proxy=proxy,
                                       accept_downloads=True)
        await _run(br, ctx)
