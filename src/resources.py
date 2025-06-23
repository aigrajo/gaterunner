import os
import hashlib
from urllib.parse import urlparse
import json
from .utils import RESOURCE_DIRS

def get_filename_from_url(url, ext=''):
    path = urlparse(url).path
    filename = os.path.basename(path) or 'index'
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:8]
    name, orig_ext = os.path.splitext(filename)
    if not orig_ext and ext:
        orig_ext = ext
    return f'{name}_{url_hash}{orig_ext}'

async def handle_request(request, resource_urls):
    if request.resource_type in {"document", "stylesheet", "script", "image", "font", "media"}:
        print(f"[RESOURCE] {request.resource_type.upper()}: {request.url}")
        resource_urls.add(request.url)

async def handle_response(response, output_dir, url_to_local, resource_response_headers, stats):
    req = response.request
    if req.resource_type not in {"document", "stylesheet", "script", "image", "font", "media"}:
        return

    url2 = response.url
    resource_response_headers[url2] = {
        "status_code": response.status,
        "headers": dict(response.headers),
    }

    # Derive file-extension from Content-Type
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
        stats["errors"] += 1

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)

async def save_screenshot(page, output_dir):
    try:
        await page.screenshot(path=f"{output_dir}/screenshot.png", full_page=True)
    except Exception:
        print("[WARN] Could not take screenshot; page already closed")