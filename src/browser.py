import os
import asyncio
from playwright.async_api import async_playwright, Error

from .context import create_context
from .gaterunner import run_gates
from .resources import handle_request, handle_response, save_json, save_screenshot
from .html import save_html_files

async def save_page(url: str, output_dir: str, *, gates_enabled=None, gate_args=None):
    """
    Save page resources
    """""
    gates_enabled = gates_enabled or {}
    gate_args = gate_args or {}

    resource_urls = set()
    resource_request_headers = {}
    resource_response_headers = {}
    url_to_local = {}
    stats = {"warnings": 0, "errors": 0}

    async with async_playwright() as p:
        browser, context = await create_context(p, gate_args)

        await run_gates(None, context, gates_enabled=gates_enabled, gate_args=gate_args, url=url, resource_request_headers=resource_request_headers)
        page = await context.new_page()

        # Wire up request/response capture
        page.on("request", lambda req: asyncio.create_task(handle_request(req, resource_urls)))
        page.on("response", lambda resp: asyncio.create_task(handle_response(resp, output_dir, url_to_local, resource_response_headers, stats)))

        # Navigate & wait until the network is *truly* idle
        print(f"[INFO] Loading page: {url}")
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
        except Exception as exc:
            print(f"[ERROR] Failed to load {url}: {exc}")
            stats["errors"] += 1
            await browser.close()
            return

        # Trigger any lazy‑load by scrolling to bottom
        scroll_script = """
            async () => {
                await new Promise(resolve => {
                    let totalHeight = 0;
                    const distance = 100;
                    const timer = setInterval(() => {
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        if (totalHeight >= document.body.scrollHeight) {
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
        """
        try:
            await page.evaluate(scroll_script)
        except Error:
            pass

        # Capture screenshot, HTML, cookies
        os.makedirs(output_dir, exist_ok=True)
        if not page.is_closed():
            await save_screenshot(page, output_dir)

        save_json(os.path.join(output_dir, "http_request_headers.json"), resource_request_headers)
        save_json(os.path.join(output_dir, "http_response_headers.json"), resource_response_headers)

        cookies = await context.cookies()
        save_json(os.path.join(output_dir, "cookies.json"), cookies)

        # Grab DOM; guard against closed page
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