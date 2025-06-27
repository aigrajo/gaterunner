"""
browser.py – drive Playwright, follow redirects, save downloads.
"""

from __future__ import annotations
import asyncio, os
from contextlib import suppress
from pathlib import Path
from playwright.async_api import async_playwright, Error

try:
    from camoufox.async_api import AsyncCamoufox   # type: ignore
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

# ───────── download helper ─────────

async def _save_download(dl, out_dir: str):
    name = dl.suggested_filename or _fname_from_url(dl.url, "")
    dst = Path(out_dir) / "downloads" / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    await dl.save_as(dst)
    print(f"[DOWNLOAD] Saved: {dst.name}")

# ───────── core work ─────────

async def _grab(
    browser,
    context,
    url: str,
    out_dir: str,
    resource_urls: set[str],
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
    await run_gates(
        None, context,
        gates_enabled=gates_enabled, gate_args=gate_args,
        url=url, resource_request_headers=req_hdrs,
    )

    page = await context.new_page()
    page.on("request", lambda r: asyncio.create_task(handle_request(r, resource_urls)))
    page.on("response", lambda r: asyncio.create_task(
        handle_response(r, out_dir, url_map, resp_hdrs, stats)))
    downloads: list[asyncio.Task] = []
    page.on("download", lambda dl: downloads.append(
        asyncio.create_task(_save_download(dl, out_dir))))

    print(f"[INFO] Loading page: {url}")
    try:
        await page.goto(url.strip(), wait_until="domcontentloaded", timeout=0)
    except Error as exc:
        msg = str(exc)
        if ("Download is starting" in msg) or ("net::ERR_ABORTED" in msg):
            print("[INFO] Navigation converted to download; DOM skipped")
        else:
            print(f"[ERROR] Failed to load {url}: {exc}")
            stats["errors"] += 1

    if downloads:
        await asyncio.gather(*downloads, return_exceptions=True)

    # basic scroll (if page still open)
    if not page.is_closed():
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_load_state("networkidle")

    # artefacts ------------------------------------------------------------
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

    print(f"Captured {len(resource_urls)} resources")
    print(f"warnings={stats['warnings']} errors={stats['errors']}")
    await browser.close()

# ───────── public API ─────────

async def save_page(
    url: str, out_dir: str,
    *, gates_enabled=None, gate_args=None, proxy=None,
):
    gates_enabled = gates_enabled or {}
    gate_args = gate_args or {}

    pause_ms = gate_args.get("scroll_pause_ms", 150)
    max_scrolls = gate_args.get("max_scrolls")

    res_urls: set[str] = set()
    req_hdrs, resp_hdrs, url_map = {}, {}, {}
    stats = {"warnings": 0, "errors": 0}

    async def _run(br, ctx):
        await _grab(
            br, ctx, url, out_dir,
            res_urls, req_hdrs, resp_hdrs, url_map, stats,
            pause_ms=pause_ms, max_scrolls=max_scrolls,
            gates_enabled=gates_enabled, gate_args=gate_args,
        )

    if gates_enabled.get("UserAgentGate", True):
        if _HAS_CAMOUFOX and "Firefox" in gate_args.get("UserAgentGate", {}).get("user_agent", ""):
            print("[INFO] Launching CamouFox browser…")
            async with AsyncCamoufox(headless=True, proxy=proxy, geoip=True) as br:
                ctx = await br.new_context(accept_downloads=True)
                await _run(br, ctx)
        else:
            async with async_playwright() as p:
                br, ctx = await create_context(p, gate_args, proxy=proxy, accept_downloads=True)
                await _run(br, ctx)
    else:
        async with async_playwright() as p:
            br, ctx = await create_context(p, gate_args, proxy=proxy, accept_downloads=True)
            await _run(br, ctx)
