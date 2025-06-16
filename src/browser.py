import os
import json
import asyncio
import aiohttp
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from .resources import save_resource
from .html import rewrite_html_resources
from .gates import ALL_GATES

async def run_gates(page, context, geolocation=None, url=None):
    for gate in ALL_GATES:
        handled = await gate.handle(page, context, geolocation=geolocation, url=url)
        if handled:
            print(f"[GATE] {gate.name} handled.")

async def save_page(url, output_dir, geolocation=None):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        context_args = {}
        if geolocation:
            context_args["geolocation"] = geolocation

        context = await browser.new_context(**context_args)
        await run_gates(None, context, geolocation=geolocation, url=url)

        page = await context.new_page()

        # Capture all network requests
        resource_urls = set()

        async def handle_request(request):
            if request.resource_type in ['document', 'stylesheet', 'script', 'image', 'font', 'media']:
                print(f"[RESOURCE] {request.resource_type.upper()}: {request.url}")
                resource_urls.add(request.url)

        page.on('request', handle_request)

        print(f'[INFO] Loading page: {url}')

        try:
            await page.goto(url, wait_until='domcontentloaded')
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            print(f'[ERROR] Failed to load {url}: {e}')
            await browser.close()
            return

        # Take screenshot
        await page.screenshot(path=f"{output_dir}/screenshot.png", full_page=True)

        scroll_script = """
            async () => {
                await new Promise(resolve => {
                    let totalHeight = 0;
                    let distance = 100;
                    let timer = setInterval(() => {
                        window.scrollBy(0, distance);
                        totalHeight += distance;

                        if (totalHeight >= document.body.scrollHeight){
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
        """

        # Scroll to bottom to trigger lazy loading
        await page.evaluate(scroll_script)

        print(f'Captured {len(resource_urls)} resources')

        # Save cookies
        cookies = await context.cookies()
        with open(os.path.join(output_dir, 'cookies.json'), 'w') as f:
            json.dump(cookies, f, indent=2)

        # Save HTML
        html_content = await page.content()
        html_path = os.path.join(output_dir, 'page.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Save resources
        async with aiohttp.ClientSession() as session:
            tasks = []
            for res_url in resource_urls:
                task = save_resource(session, res_url, output_dir)
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            url_to_local = {}
            for result in results:
                if result:
                    filename, original_url = result
                    url_to_local[original_url] = filename

        # Rewrite HTML links (basic string replace)
        html_content = rewrite_html_resources(html_content, url_to_local)

        # Save updated HTML
        updated_html_path = os.path.join(output_dir, 'page_offline.html')
        with open(updated_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        await browser.close()