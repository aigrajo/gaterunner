"""
resources.py – save network responses useful for analysis.
"""

from __future__ import annotations
import hashlib, json, os, re
from urllib.parse import urlparse
from playwright.async_api import Error
from .utils import RESOURCE_DIRS

_FILENAME_RE = re.compile(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)')

def _guess_ext(ct: str) -> str:
    if "text/css" in ct:            return ".css"
    if "javascript" in ct:          return ".js"
    if ct.startswith("image/"):     return "." + ct.split("/")[1].split(";")[0]
    if ct.startswith("font/"):      return "." + ct.split("/")[1].split(";")[0]
    if "html" in ct:                return ".html"
    if "pdf" in ct:                 return ".pdf"
    if "exe" in ct:                 return ".exe"
    if "zip" in ct:                 return ".zip"
    return ""

def _fname_from_cd(cd: str | None) -> str | None:
    if not cd:
        return None
    m = _FILENAME_RE.search(cd)
    return m.group(1) if m else None

def _fname_from_url(url: str, ext: str) -> str:
    stem, orig_ext = os.path.splitext(os.path.basename(urlparse(url).path) or "index")
    if not orig_ext and ext:
        orig_ext = ext
    h = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{stem}_{h}{orig_ext}"

# ───────────────────────── Hooks ──────────────────────────

async def handle_request(request, resource_urls: set[str]):
    if request.resource_type in {
        "document", "stylesheet", "script", "image",
        "font", "media", "other"
    }:
        print(f"[RESOURCE] {request.resource_type.upper()}: {request.url}")
        resource_urls.add(request.url)

async def handle_response(
    response,
    output_dir: str,
    url_to_local: dict[str, str],
    resp_hdrs: dict[str, dict],
    stats: dict,
):
    req_type = response.request.resource_type
    if req_type not in {
        "document", "stylesheet", "script", "image",
        "font", "media", "other"
    }:
        return

    url = response.url
    resp_hdrs[url] = {"status_code": response.status,
                      "headers": dict(response.headers)}

    # nothing useful to save for redirects
    if 300 <= response.status < 400:
        return

    ct = response.headers.get("content-type", "")
    cd = response.headers.get("content-disposition", "")
    ext = _guess_ext(ct) or os.path.splitext(urlparse(url).path)[1]
    fname = _fname_from_cd(cd) or _fname_from_url(url, ext)

    subdir = RESOURCE_DIRS.get(req_type, "other")
    dirpath = os.path.join(output_dir, subdir) if subdir else output_dir
    os.makedirs(dirpath, exist_ok=True)
    fpath = os.path.join(dirpath, fname)
    url_to_local[url] = os.path.relpath(fpath, output_dir)

    try:
        body = await response.body()
        if body:
            with open(fpath, "wb") as fh:
                fh.write(body)
    except Error as e:
        # Expected for downloads (no body accessible) – warn, don’t error
        if "Network.getResponseBody" in str(e):
            print(f"[WARN] Body unavailable (download): {url}")
            return
        print(f"[ERROR] Could not save {url}: {e}")
        stats["errors"] += 1

# ───────────────────────── Utils ──────────────────────────

def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)

async def save_screenshot(page, out_dir: str):
    try:
        await page.screenshot(path=f"{out_dir}/screenshot.png", full_page=True)
    except Exception:
        print("[WARN] screenshot failed (page closed)")
