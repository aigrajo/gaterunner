import os
import asyncio

# Core Playwright imports
from playwright.async_api import async_playwright, Error

# Optional native‑stealth browser (CamouFox)
try:
    # AsyncCamoufox exposes the same API surface as Playwright's Browser
    from camoufox.async_api import AsyncCamoufox  # type: ignore
    _HAS_CAMOUFOX = True
except ImportError:  # fallback to JS‑only stealth
    _HAS_CAMOUFOX = False

from .context import create_context  # JS stealth fallback
from .gaterunner import run_gates
from .resources import (
    handle_request,
    handle_response,
    save_json,
    save_screenshot,
)
from .html import save_html_files


async def auto_scroll(page, *, pause_ms: int = 150, max_scrolls: int | None = None):
    """Scroll down one viewport at a time until height stops growing."""

    await page.evaluate(
        """
        async ({ pause, cap }) => {
            const sleep = ms => new Promise(r => setTimeout(r, ms));
            let lastHeight = 0;
            let count = 0;

            for (;;) {
                const { scrollHeight, clientHeight } = document.documentElement;
                window.scrollBy(0, clientHeight);
                await sleep(pause);

                const newHeight = document.documentElement.scrollHeight;
                if (newHeight === lastHeight) break;
                if (cap !== null && ++count >= cap) break;
                lastHeight = newHeight;
            }
        }
        """,
        {"pause": pause_ms, "cap": max_scrolls},
    )


async def _grab(
    browser,
    context,
    url: str,
    output_dir: str,
    resource_urls: set[str],
    request_headers: dict,
    response_headers: dict,
    url_to_local: dict,
    stats: dict,
    *,
    pause_ms: int,
    max_scrolls: int | None,
    gates_enabled,
    gate_args,
):
    """Shared capture logic – agnostic of the browser implementation."""
    await run_gates(
        None,
        context,
        gates_enabled=gates_enabled,
        gate_args=gate_args,
        url=url,
        resource_request_headers=request_headers,
    )

    page = await context.new_page()

    # Network capture hooks
    page.on("request", lambda req: asyncio.create_task(handle_request(req, resource_urls)))
    page.on(
        "response",
        lambda resp: asyncio.create_task(
            handle_response(resp, output_dir, url_to_local, response_headers, stats)
        ),
    )

    print(f"[INFO] Loading page: {url}")
    try:
        await page.goto(url, wait_until="domcontentloaded")
        await auto_scroll(page, pause_ms=pause_ms, max_scrolls=max_scrolls)
        await page.wait_for_load_state("networkidle")
    except Exception as exc:
        print(f"[ERROR] Failed to load {url}: {exc}")
        stats["errors"] += 1
        await browser.close()
        return

    # Persist screenshot and metadata
    os.makedirs(output_dir, exist_ok=True)
    if not page.is_closed():
        await save_screenshot(page, output_dir)

    save_json(os.path.join(output_dir, "http_request_headers.json"), request_headers)
    save_json(os.path.join(output_dir, "http_response_headers.json"), response_headers)

    cookies = await context.cookies()
    save_json(os.path.join(output_dir, "cookies.json"), cookies)

    # Save DOM
    html_content = ""
    if not page.is_closed():
        try:
            html_content = await page.content()
        except Error:
            print("[WARN] Could not read page content; window closed itself")
            stats["warnings"] += 1
    if html_content:
        save_html_files(output_dir, html_content, url_to_local)

    print(f"Captured {len(resource_urls)} resources")
    print(f"warnings={stats['warnings']} errors={stats['errors']}")
    await browser.close()


async def save_page(
    url: str,
    output_dir: str,
    *,
    gates_enabled: dict | None = None,
    gate_args: dict | None = None,
):
    """Entry‑point: capture a page using CamouFox if available, else fallback."""

    gates_enabled = gates_enabled or {}
    gate_args = gate_args or {}

    # Scroll settings pulled from gate_args to preserve old behaviour
    pause_ms: int = gate_args.get("scroll_pause_ms", 150)
    max_scrolls: int | None = gate_args.get("max_scrolls")

    resource_urls: set[str] = set()
    request_headers: dict = {}
    response_headers: dict = {}
    url_to_local: dict = {}
    stats = {"warnings": 0, "errors": 0}

    if gates_enabled.get('UserAgentGate', True):
        if _HAS_CAMOUFOX and "Firefox" in gate_args['UserAgentGate'].get("user_agent"):
            # Native‑stealth path – no JS patches needed
            print("[INFO] Launching CamouFox browser...")
            async with AsyncCamoufox(headless=False) as browser:  # type: ignore
                context = await browser.new_context()
                await _grab(
                    browser,
                    context,
                    url,
                    output_dir,
                    resource_urls,
                    request_headers,
                    response_headers,
                    url_to_local,
                    stats,
                    pause_ms=pause_ms,
                    max_scrolls=max_scrolls,
                    gates_enabled=gates_enabled,
                    gate_args=gate_args,
                )
        else:
            # Playwright + JS‑stealth patches
            async with async_playwright() as p:
                browser, context = await create_context(p, gate_args)
                await _grab(
                    browser,
                    context,
                    url,
                    output_dir,
                    resource_urls,
                    request_headers,
                    response_headers,
                    url_to_local,
                    stats,
                    pause_ms=pause_ms,
                    max_scrolls=max_scrolls,
                    gates_enabled=gates_enabled,
                    gate_args=gate_args,
                )
    else:
        # Playwright without User Agent Spoofing
        async with async_playwright() as p:
            browser, context = await create_context(p, gate_args)
            await _grab(
                browser,
                context,
                url,
                output_dir,
                resource_urls,
                request_headers,
                response_headers,
                url_to_local,
                stats,
                pause_ms=pause_ms,
                max_scrolls=max_scrolls,
                gates_enabled=gates_enabled,
                gate_args=gate_args,
            )
