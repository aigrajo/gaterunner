import os
import json
import asyncio
import hashlib
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Error

from src.clienthints import (
    send_ch,
    parse_chromium_version,
    parse_chromium_ua,
    extract_high_entropy_hints,
    parse_chromium_full_version,
)
from .html import rewrite_html_resources
from .gates import ALL_GATES
from .map import RESOURCE_DIRS

def get_filename_from_url(url, ext=''):
    path = urlparse(url).path
    filename = os.path.basename(path) or 'index'

    # Add hash to ensure uniqueness
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:8]
    name, orig_ext = os.path.splitext(filename)
    if not orig_ext and ext:
        orig_ext = ext
    return f'{name}_{url_hash}{orig_ext}'

async def run_gates(page, context, gates_enabled=None, gate_args=None, url=None):
    gates_enabled = gates_enabled or {}
    gate_args = gate_args or {}

    # Run all handle() methods
    for gate in ALL_GATES:
        if gates_enabled.get(gate.name, True):
            args = gate_args.get(gate.name, {})
            await gate.handle(page, context, **args, url=url)

    # Collect headers
    headers = {}
    for gate in ALL_GATES:
        if gates_enabled.get(gate.name, True):
            args = gate_args.get(gate.name, {})
            gate_headers = await gate.get_headers(**args, url=url)
            headers.update(gate_headers)

    # Send headers through one route
    async def route_handler(route, request):
        merged_headers = request.headers.copy()
        merged_headers.update(headers)

        # Remove client hints headers if applicable
        filtered_headers = merged_headers.copy()
        if gates_enabled.get("UserAgentGate", True):
            client_hints = send_ch(str(gate_args.get("UserAgentGate")))
            if not client_hints:
                filtered_headers = {k: v for k, v in merged_headers.items() if not k.lower().startswith("sec-ch-ua")}


        resource_request_headers[request.url] =  {
            "method": request.method,
        }
        resource_request_headers[request.url].update(dict(filtered_headers))

        await route.continue_(headers=filtered_headers)

    await context.route("**/*", route_handler)


# Capture all network requests and responses
resource_urls = set()
pending_responses = set()
all_responses_handled = asyncio.Event()
resource_request_headers = {}
resource_response_headers = {}
url_to_local = {}

# Save page resources
async def save_page(url: str, output_dir: str, *, gates_enabled=None, gate_args=None):
    """Download *url* and its sub‑resources to *output_dir* for offline replay."""
    gates_enabled = gates_enabled or {}
    gate_args = gate_args or {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Build browser context respecting any gate options
        context_args = {}
        user_agent = None
        if "GeolocationGate" in (gate_args or {}):
            geo = gate_args["GeolocationGate"].get("geolocation")
            if geo:
                context_args["geolocation"] = geo
        if "UserAgentGate" in (gate_args or {}):
            user_agent = gate_args["UserAgentGate"].get("user_agent")
            if user_agent:
                context_args["user_agent"] = user_agent

        context = await browser.new_context(**context_args)

        # Push JS to spoof high‑entropy Client Hints
        if user_agent:
            brand, brand_v = parse_chromium_ua(user_agent)
            chromium_v = parse_chromium_version(user_agent)
            entropy = extract_high_entropy_hints(user_agent)

            with open("src/js/spoof_useragent.js", "r", encoding="utf-8") as fh:
                template = fh.read()

            js_script = template.format(
                chromium_v=chromium_v or "",
                brand=brand or "",
                brand_v=brand_v or "",
                architecture=entropy.get("architecture", ""),
                bitness=entropy.get("bitness", ""),
                wow64=str(entropy.get("wow64", False)).lower(),
                model=entropy.get("model", ""),
                mobile=str("mobile" in user_agent.lower()).lower(),
                platform=entropy.get("platform", ""),
                platformVersion=entropy.get("platformVersion", ""),
                uaFullVersion=parse_chromium_full_version(user_agent) or "",
            )
            await context.add_init_script(js_script)

        # Stealth ‑ hide webdriver flag
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        #
        # Prepare page and gates
        #
        await run_gates(None, context, gates_enabled=gates_enabled, gate_args=gate_args, url=url)
        page = await context.new_page()


        # Wire up request/response capture
        async def handle_request(request):
            if request.resource_type in {"document", "stylesheet", "script", "image", "font", "media"}:
                print(f"[RESOURCE] {request.resource_type.upper()}: {request.url}")
                resource_urls.add(request.url)

        async def handle_response(response):
            req = response.request
            if req.resource_type not in {"document", "stylesheet", "script", "image", "font", "media"}:
                return

            url2 = response.url
            resource_response_headers[url2] = {
                "status_code": response.status,
                "headers": dict(response.headers),
            }

            # Derive file‑extension from Content‑Type
            ct = response.headers.get("content-type", "")
            ext = ""
            if "text/css" in ct:
                ext = ".css"
            elif "javascript" in ct:
                ext = ".js"
            elif "image/" in ct:
                ext = "." + ct.split("/")[1].split(";")[0]
            elif "font/" in ct:
                ext = "." + ct.split("/")[1].split(";")[0]
            elif "html" in ct:
                ext = ".html"

            subdir = RESOURCE_DIRS.get(req.resource_type, "other")
            basename = get_filename_from_url(url2, ext)
            dirpath = os.path.join(output_dir, subdir) if subdir else output_dir
            os.makedirs(dirpath, exist_ok=True)
            filepath = os.path.join(dirpath, basename)
            url_to_local[url2] = os.path.relpath(filepath, output_dir)

            try:
                body = await response.body()
                with open(filepath, "wb") as fh:
                    fh.write(body)
            except Exception as exc:
                print(f"[ERROR] Could not save {url2}: {exc}")

        page.on("request", handle_request)
        page.on("response", handle_response)

        # Navigate & wait until the network is *truly* idle
        print(f"[INFO] Loading page: {url}")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)  # 30 s
            await page.wait_for_load_state("networkidle")
        except Exception as exc:
            print(f"[ERROR] Failed to load {url}: {exc}")
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
            # Ignore if page closed itself during scrolling
            pass

        # Capture screenshot, HTML, cookies
        os.makedirs(output_dir, exist_ok=True)
        if not page.is_closed():
            try:
                await page.screenshot(path=f"{output_dir}/screenshot.png", full_page=True)
            except Error:
                print("[WARN] Could not take screenshot; page already closed")

        with open(os.path.join(output_dir, "http_request_headers.json"), "w", encoding="utf-8") as fh:
            json.dump(resource_request_headers, fh, indent=2)
        with open(os.path.join(output_dir, "http_response_headers.json"), "w", encoding="utf-8") as fh:
            json.dump(resource_response_headers, fh, indent=2)

        # Save cookies even if page died – context is still alive
        cookies = await context.cookies()
        with open(os.path.join(output_dir, "cookies.json"), "w", encoding="utf-8") as fh:
            json.dump(cookies, fh, indent=2)

        # Grab DOM; guard against closed page
        html_content = ""
        if not page.is_closed():
            try:
                html_content = await page.content()
            except Error:
                print("[WARN] Could not read page content; window closed itself")
        if html_content:
            # Save raw HTML
            with open(os.path.join(output_dir, "page.html"), "w", encoding="utf-8") as fh:
                fh.write(html_content)

            # Rewrite resource links for offline use and save second copy
            offline_html = rewrite_html_resources(html_content, url_to_local)
            with open(os.path.join(output_dir, "page_offline.html"), "w", encoding="utf-8") as fh:
                fh.write(offline_html)

        print(f"Captured {len(resource_urls)} resources")
        await browser.close()
