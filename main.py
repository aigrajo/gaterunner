import asyncio
import re

from playwright.async_api import async_playwright
import os
import sys
import hashlib
import mimetypes
import aiohttp
from urllib.parse import urlparse
import json
from bs4 import BeautifulSoup

def rewrite_html_resources(html_content, url_to_local):
    soup = BeautifulSoup(html_content, "html.parser")

    tag_attr_map = {
        'img': ['src', 'srcset'],
        'script': ['src'],
        'link': ['href'],
        'iframe': ['src'],
        'audio': ['src'],
        'video': ['src', 'poster'],
        'source': ['src', 'srcset'],
        'embed': ['src'],
        'object': ['data'],
    }

    for tag, attrs in tag_attr_map.items():
        for element in soup.find_all(tag):
            for attr in attrs:
                if element.has_attr(attr):
                    original = element[attr]
                    if attr == 'srcset':
                        new_srcset = []
                        for part in original.split(','):
                            url_part = part.split(' ')[0]
                            if url_part in url_to_local:
                                part = part.replace(url_part, url_to_local[url_part])
                            new_srcset.append(part)
                        element[attr] = ', '.join(new_srcset)
                    elif original in url_to_local:
                        element[attr] = url_to_local[original]

    for element in soup.find_all(style=True):
        style = element['style']
        urls = re.findall(r'url\(([^)]+)\)', style)
        for url in urls:
            clean_url = url.strip('\'"')
            if clean_url in url_to_local:
                local_url = url_to_local[clean_url]
                style = style.replace(url, f'"{local_url}"')
        element['style'] = style

    return str(soup)

async def save_resource(session, url, output_dir):
    parsed_url = urlparse(url)
    if not parsed_url.scheme.startswith('http'):
        return None

    try:
        async with session.get(url, timeout=20) as response:
            content = await response.read()
            content_type = response.content_type or ''

            # Generate filename
            hash_digest = hashlib.md5(url.encode()).hexdigest()
            ext = mimetypes.guess_extension(response.content_type or '') or ''
            filename = f'{hash_digest}{ext}'

            if 'image' in content_type:
                subfolder = 'images'
            elif 'javascript' in content_type:
                subfolder = 'scripts'
            elif 'css' in content_type:
                subfolder = 'style'
            elif 'font' in content_type:
                subfolder = 'fonts'
            elif 'audio' in content_type:
                subfolder = 'audio'
            elif 'video' in content_type:
                subfolder = 'video'
            elif 'html' in content_type:
                subfolder = 'html'
            else:
                subfolder = 'other'


            subdir_path = os.path.join(output_dir, subfolder)
            os.makedirs(subdir_path, exist_ok=True)

            filepath = os.path.join(subdir_path, filename)
            with open(filepath, 'wb') as f:
                f.write(content)

            relative_path = os.path.join(subfolder, filename)
            return relative_path, url

    except Exception as e:
        print(f'Failed to download {url}: {e}')
        return None

async def save_page(url, output_dir):

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
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
                filename = result
                original_url = result
                if filename:
                    url_to_local[original_url] = filename

        # Rewrite HTML links (basic string replace)
        html_content = rewrite_html_resources(html_content, url_to_local)

        # Save updated HTML
        updated_html_path = os.path.join(output_dir, 'page_offline.html')
        with open(updated_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        await browser.close()

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <url>")
        sys.exit(1)

    url_to_save = sys.argv[1]

    # Default output dir: saved_<domain>
    parsed_url = urlparse(url_to_save)
    domain = parsed_url.netloc.replace(':', '_')  # sanitize
    output_folder = f'./data/saved_{domain}'

    print(f'Output directory: {output_folder}')

    asyncio.run(save_page(url_to_save, output_folder))

if __name__ == '__main__':
    main()
