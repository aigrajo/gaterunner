import os
import json
import asyncio
import hashlib
from platform import architecture

from playwright.async_api import async_playwright
from urllib.parse import urlparse

from src.clienthints import send_ch, parse_chromium_version, \
    parse_chromium_ua, extract_high_entropy_hints, parse_chromium_full_version
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
async def save_page(url, output_dir, gates_enabled=None, gate_args=None):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Set context arguments
        context_args = {}
        if gate_args:
            if 'GeolocationGate' in gate_args:
                geo = gate_args['GeolocationGate'].get('geolocation')
                if geo:
                    context_args['geolocation'] = geo
            if 'UserAgentGate' in gate_args:
                user_agent = gate_args['UserAgentGate'].get('user_agent')
                if user_agent:
                    context_args['user_agent'] = user_agent
        context = await browser.new_context(**context_args)

        # Set client hints in context
        if 'UserAgentGate' in gate_args:
            brand, brand_v = parse_chromium_ua(user_agent)
            chromium_v = parse_chromium_version(user_agent)
            entropy = extract_high_entropy_hints(user_agent)

            with open("src/js/spoof_useragent.js", "r") as f:
                js_template = f.read()

            js_script = js_template.format(
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


        # Set navigator.webdriver to false
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")


        # Set gates
        await run_gates(None, context, gates_enabled=gates_enabled, gate_args=gate_args, url=url)

        page = await context.new_page()


        async def handle_request(request):
            if request.resource_type in ['document', 'stylesheet', 'script', 'image', 'font', 'media']:
                print(f"[RESOURCE] {request.resource_type.upper()}: {request.url}")
                resource_urls.add(request.url)
                pending_responses.add(request.url)

        async def handle_response(response):

            url2 = response.url

            resource_response_headers[url2] = {
                "status_code": response.status,
            }
            resource_response_headers[url2].update(dict(response.headers))

            if response.request.resource_type in ['document', 'stylesheet', 'script', 'image', 'font', 'media']:
                # Generate a safe filename
                resource_type = response.request.resource_type
                subdir = RESOURCE_DIRS.get(resource_type, 'other')
                ct = response.headers.get('content-type', '')
                ext = ''
                if 'text/css' in ct:
                    ext = '.css'
                elif 'javascript' in ct:
                    ext = '.js'
                elif 'image/' in ct:
                    ext = '.' + ct.split('/')[1].split(';')[0]
                elif 'font/' in ct:
                    ext = '.' + ct.split('/')[1].split(';')[0]
                elif 'html' in ct:
                    ext = '.html'

                basename = get_filename_from_url(url2)
                if not os.path.splitext(basename)[1] and ext:
                    basename = basename + ext

                request = response.request
                resource_request_headers[request.url] = {
                    "method": request.method,
                }
                resource_request_headers[request.url] = dict(request.headers)

                # Compose full path
                if subdir:
                    dirpath = os.path.join(output_dir, subdir)
                    os.makedirs(dirpath, exist_ok=True)
                    filepath = os.path.join(dirpath, basename)
                    url_to_local[url2] = os.path.join(subdir, basename)
                else:
                    filepath = os.path.join(output_dir, basename)
                    url_to_local[url2] = basename

                try:
                    body = await response.body()
                    with open(filepath, 'wb') as fi:
                        fi.write(body)
                except Exception as ex:
                    print(f"[ERROR] Could not save {url2}: {ex}")

            # Wait until all resources are loaded
            pending_responses.discard(url2)
            if not pending_responses:
                all_responses_handled.set()

        # Load requests and responses
        page.on('request', handle_request)
        page.on('response', handle_response)

        print(f'[INFO] Loading page: {url}')


        try:
            await page.goto(url, wait_until='domcontentloaded')
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            print(f'[ERROR] Failed to load {url}: {e}')
            await browser.close()
            return

        try:
            await asyncio.wait_for(all_responses_handled.wait(), timeout=10)
        except asyncio.TimeoutError:
            print('[ERROR] Timeout waiting for response.')

        # Take screenshot
        await page.screenshot(path=f"{output_dir}/screenshot.png", full_page=True)

        # Write resource http request headers
        headers_path = os.path.join(output_dir, 'http_request_headers.json')
        with open(headers_path, 'w', encoding='utf-8') as f:
            json.dump(resource_request_headers, f, indent=2)

        # Write resource http response headers
        headers_path = os.path.join(output_dir, 'http_response_headers.json')
        with open(headers_path, 'w', encoding='utf-8') as f:
            json.dump(resource_response_headers, f, indent=2)

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

        # Rewrite HTML links (basic string replace)
        html_content = rewrite_html_resources(html_content, url_to_local)

        # Save updated HTML
        updated_html_path = os.path.join(output_dir, 'page_offline.html')
        with open(updated_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        await browser.close()