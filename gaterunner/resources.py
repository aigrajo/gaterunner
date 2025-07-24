"""
resources.py – Network response handling and resource management

This module handles:
- Intercepting and saving network responses (images, scripts, stylesheets, etc.)
- Managing HTTP headers and cookies
- Handling file downloads via CDP (Chrome DevTools Protocol)
- Providing fallback HTTP fetching when Playwright body access fails
- Organizing saved resources into appropriate directory structures

Key classes:
- ResourceData: Tracks all captured resources and metadata
"""


import hashlib
import json
import os
import re
import urllib
from pathlib import Path
from urllib.parse import urlparse
from dataclasses import dataclass, field
from typing import Optional
import httpx, aiofiles
from httpx import HTTPStatusError

from playwright.async_api import Error
from playwright._impl._errors import Error as CDPError
from gaterunner.debug import debug_print
from gaterunner.utils import safe_filename, dedup_path

# ─── Constants ───────────────────────────────────────────────
HTTP_FETCH_TIMEOUT_SEC = 30  # Timeout for fallback HTTP requests
STREAM_CHUNK_SIZE = 65536  # Streaming download chunk size
MAX_URL_LOG_LENGTH = 80  # Truncate URLs in logs for readability

# ───────────────────────── data structures ──────────────────────────

@dataclass
class ResourceData:
    """Bundle all resource tracking data together."""
    urls: set = field(default_factory=set)
    request_headers: dict = field(default_factory=dict)  
    response_headers: dict = field(default_factory=dict)
    url_to_file: dict = field(default_factory=dict)
    stats: dict = field(default_factory=lambda: {"downloads": 0, "warnings": 0, "errors": 0})

# ───────────────────────── constants ──────────────────────────

# Resource directory mapping - moved from utils.py
RESOURCE_DIRS: dict[str, str] = {
    'image': 'images',
    'script': 'scripts',
    'stylesheet': 'stylesheets',
    'font': 'fonts',
    'media': 'media',
    'document': 'html',
}

# ───────────────────────── constants ──────────────────────────

# Constants moved to utils.py for shared use

_FILENAME_RE = re.compile(
    r"""
        filename\*?=            # filename OR filename*
        (?:UTF-8''|[\"'])?     # optional RFC5987 charset/lang prefix or leading quote
        (?P<name>[^;\"']+)     # the actual file‑name (stop at ; or quote)
    """,
    re.I | re.X,
)

_FILENAME_STAR_RE = re.compile(
    r"""filename\*\s*=\s*[^'"]+'[^']*'(?P<enc>[^;]+)""", re.I
)

_BINARY_MIME_SNIPPETS: tuple[str, ...] = (
    "application/pdf",
    "application/zip",
    "application/x-msdownload",
    "application/vnd.microsoft.portable-executable",
    "application/octet-stream",
)

# ───────────────────────── helpers ──────────────────────────

def _validate_metadata_completeness(url: str, resources: ResourceData, context: str = ""):
    """Validate that both file mapping and response headers are present for a URL.
    
    @param url (str): The URL to check metadata for.
    @param resources (ResourceData): Resource tracking data structure.
    @param context (str): Context string for logging (e.g., "CDP", "stream_fetch").
    
    @return None
    """
    missing = []
    if url not in resources.url_to_file:
        missing.append("url_to_file")
    if url not in resources.response_headers:
        missing.append("response_headers")
    
    if missing:
        print(f"[WARN] {context} Missing metadata for {url[:MAX_URL_LOG_LENGTH]}…: {', '.join(missing)}")
    else:
        debug_print(f"[DEBUG] {context} Complete metadata saved for {url[:MAX_URL_LOG_LENGTH]}…")


def _guess_ext(ct: str) -> str:
    """Infer file extension based on Content-Type header.

    @param ct (str): MIME type string (e.g. 'text/html', 'image/png').

    @return (str): File extension with leading dot (e.g. '.html'). Empty string if unknown.
    """

    ct_low = ct.lower()
    if "text/css" in ct_low:
        return ".css"
    if "javascript" in ct_low:
        return ".js"
    if ct_low.startswith("image/"):
        return "." + ct_low.split("/", 1)[1].split(";", 1)[0]
    if ct_low.startswith("font/"):
        return "." + ct_low.split("/", 1)[1].split(";", 1)[0]
    if "html" in ct_low:
        return ".html"
    if "pdf" in ct_low:
        return ".pdf"
    if "zip" in ct_low:
        return ".zip"
    if "exe" in ct_low:
        return ".exe"
    return ""


# _safe_filename moved to utils.py as safe_filename


def _fname_from_cd(cd: Optional[str]) -> Optional[str]:
    """Extract filename from Content-Disposition header.

    @param cd (Optional[str]): The Content-Disposition header value.

    @return (Optional[str]): Filename if extractable. None if not present or invalid.
    """

    if not cd:
        return None

    # 1 RFC 5987 path: filename*=
    m = _FILENAME_STAR_RE.search(cd)
    if m:
        raw = urllib.parse.unquote(m["enc"])
        stem, ext = os.path.splitext(os.path.basename(raw))
        return safe_filename(stem or "download", ext, raw)

    # 2 Legacy path: filename=
    m = _FILENAME_RE.search(cd)
    if m:
        raw_name = m.group("name").strip("\"'")
        stem, ext = os.path.splitext(os.path.basename(raw_name))
        return safe_filename(stem or "download", ext, raw_name)

    return None


def _fname_from_url(url: str, fallback_ext: str) -> str:
    """Generate filename from URL path, using fallback extension if needed.

    @param url (str): The full URL of the resource.
    @param fallback_ext (str): Extension to use if URL has no extension.

    @return (str): Sanitized filename derived from URL.
    """

    path = urlparse(url).path
    stem, ext = os.path.splitext(os.path.basename(path) or "index")
    if not ext and fallback_ext:
        ext = fallback_ext
    return safe_filename(stem, ext, url)


def _looks_like_download(ct: str, cd: Optional[str]) -> bool:
    """Check if response looks like a file download.

    @param ct (str): Content-Type header.
    @param cd (Optional[str]): Content-Disposition header.

    @return (bool): True if it's likely a file download. False otherwise.
    """

    cd_low = (cd or "").lower()
    if "attachment" in cd_low or "filename=" in cd_low:
        return True

    ct_low = ct.lower()
    return any(snippet in ct_low for snippet in _BINARY_MIME_SNIPPETS)

# ───────────────────────── hooks ──────────────────────────

async def handle_request(request, resources):
    """Track network requests for static resources.

    @param request (playwright.Request): The intercepted network request object.
    @param resources (ResourceData): Resource tracking data structure.

    @return None
    """

    if request.resource_type in {
        "document", "stylesheet", "script", "image", "font", "media", "other",
    }:
        print(f"[RESOURCE] {request.resource_type.upper()}: {request.url}")
        resources.urls.add(request.url)


async def handle_response(
    response,
    out_dir: str,
    resources,
):
    """Save qualifying network responses to disk and update metadata.

    @param response (playwright.Response): The intercepted network response.
    @param out_dir (str): Path to the output directory for saved resources.
    @param resources (ResourceData): Resource tracking data structure.

    @return None
    """

    req_type = response.request.resource_type
    if req_type not in {
        "document", "stylesheet", "script", "image",
        "font", "media", "xhr", "fetch", "other",
    }:
        return

    url = response.url
    
    # Always collect response headers from playwright Response (most reliable source)
    resources.response_headers[url] = {
        "status_code": response.status,
        "headers": dict(response.headers),
    }
    
    # If file was already saved by CDP interceptor, we're done
    if response.url in resources.url_to_file:
        debug_print(f"[DEBUG] Metadata updated for CDP-saved file: {url[:MAX_URL_LOG_LENGTH]}…")
        _validate_metadata_completeness(url, resources, "handle_response_post_cdp")
        return

    if 300 <= response.status < 400:
        return  # skip redirects

    ct = response.headers.get("content-type", "") or ""
    cd = response.headers.get("content-disposition", "")
    ext = _guess_ext(ct) or os.path.splitext(urlparse(url).path)[1]
    fname = _fname_from_cd(cd) or _fname_from_url(url, ext)

    is_download = _looks_like_download(ct, cd)
    dirpath = (
        os.path.join(out_dir, "downloads")
        if is_download
        else os.path.join(out_dir, RESOURCE_DIRS.get(req_type, "other"))
    )

    if len(os.path.basename(dirpath)) > 200:
        digest = hashlib.md5(dirpath.encode()).hexdigest()[:8]
        dirpath = os.path.join(
            os.path.dirname(dirpath),
            f"{os.path.basename(dirpath)[:200]}_{digest}",
        )

    os.makedirs(dirpath, exist_ok=True)

    fpath = dedup_path(Path(dirpath) / fname)
    resources.url_to_file[url] = os.path.relpath(fpath, out_dir)

    try:
        body = await response.body()
        if not body:
            raise Error("empty")
        fpath.write_bytes(body)
        if is_download:
            resources.stats["downloads"] += 1
            print(f"[DOWNLOAD] Saved: {fpath.name}")
        
        # Validate metadata completeness
        _validate_metadata_completeness(url, resources, "handle_response")

    except Error as e:
        if any(tok in str(e) for tok in ("Network.getResponseBody", "empty")):
            success = await _stream_fetch(response.request, fpath, resources, url, out_dir)
            if success:
                if is_download:
                    resources.stats["downloads"] += 1
                print(f"[DOWNLOAD] Fetched via HTTP: {fpath.name}")
                # Validate metadata after successful fallback fetch
                _validate_metadata_completeness(url, resources, "fallback_fetch")
            else:
                resources.stats["errors"] += 1
                print(f"[ERROR] Fallback fetch failed for {url[:MAX_URL_LOG_LENGTH]}…")
            return
        resources.stats["errors"] += 1
        print(f"[ERROR] Could not save {url}: {e}")

    except OSError as e:
        resources.stats["warnings"] += 1
        print(f"[WARN] Could not write {fpath.name}: {e}")

# ───────────────────────── misc helpers ──────────────────────────

def save_json(path: str, data):
    """Write Python object as JSON to disk.

    @param path (str): Destination path for the JSON file.
    @param data (any): Python object to serialize (must be JSON serializable).

    @return None
    """

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


async def save_screenshot(page, out_dir: str):
    """Capture and save a full-page screenshot.

    @param page (playwright.Page): The browser page object to screenshot.
    @param out_dir (str): Directory where the screenshot will be saved.

    @return None
    """

    try:
        await page.screenshot(path=f"{out_dir}/screenshot.png", full_page=True)
    except Exception:
        print("[WARN] screenshot failed (page closed)")

async def _stream_fetch(req, dest: Path, resources=None, url=None, out_dir=None, timeout: int = HTTP_FETCH_TIMEOUT_SEC):
    """Replay the original request outside DevTools, keeping method, body, cookies."""
    url = url or req.url
    method = req.method
    post_data = req.post_data or None
    headers = dict(req.headers)
    headers.pop("content-length", None)

    # -------- collect cookies --------
    try:
        ctx = req.frame.page.context  # ≥1.43
    except AttributeError:
        ctx = req.context  # 1.42
    try:
        cookies = {c["name"]: c["value"] for c in await ctx.cookies(url)}
    except Exception:
        cookies = {}

    # -------- stream --------
    try:
        async with httpx.AsyncClient(
                follow_redirects=True, timeout=timeout, cookies=cookies
        ) as client, client.stream(
            method, url, headers=headers, content=post_data
        ) as r:
            if r.status_code >= 400:  # server returned error page
                return False
            async with aiofiles.open(dest, "wb") as fh:
                async for chunk in r.aiter_bytes(STREAM_CHUNK_SIZE):
                    await fh.write(chunk)
            
            # Update metadata if resources object provided
            if resources and url:
                # Update response headers with HTTP response data
                if url not in resources.response_headers:
                    resources.response_headers[url] = {
                        "status_code": r.status_code,
                        "headers": dict(r.headers),
                    }
                
                # Update file mapping if not already set
                if url not in resources.url_to_file and out_dir:
                    resources.url_to_file[url] = os.path.relpath(dest, out_dir)
                
                # Validate metadata completeness
                _validate_metadata_completeness(url, resources, "stream_fetch")
                    
        return True
    except (HTTPStatusError, httpx.TransportError):
        return False

# _dedup moved to utils.py as dedup_path

async def enable_cdp_download_interceptor(
    page,
    downloads_dir,
    resources: ResourceData,
):
    from pathlib import Path
    import base64

    downloads_dir = Path(downloads_dir)            # make sure it's a Path
    cdp = await page.context.new_cdp_session(page)
    await cdp.send(
        "Fetch.enable",
        {"patterns": [{"urlPattern": "*", "requestStage": "Response"}]},
    )

    async def _on_paused(ev):
        req_id = ev["requestId"]
        url    = ev["request"]["url"]
        hdrs   = ev.get("responseHeaders", [])

        def _get(name: str):
            return next((h["value"] for h in hdrs if h["name"].lower() == name), "")
        ct, cd = _get("content-type"), _get("content-disposition")

        want = _looks_like_download(ct, cd)
        if want and not cd:
            fname = _fname_from_url(url, _guess_ext(ct))
            hdrs.append({"name": "Content-Disposition",
                         "value": f'attachment; filename="{fname}"'})

        saved = False
        if want:
            try:
                stream_id = (
                    await cdp.send("Fetch.takeResponseBodyAsStream", {"requestId": req_id})
                )["stream"]

                fname = _fname_from_cd(cd) or _fname_from_url(url, _guess_ext(ct))
                dest  = dedup_path(downloads_dir / fname)
                dest.parent.mkdir(parents=True, exist_ok=True)

                async with aiofiles.open(dest, "wb") as fh:
                    while True:
                        chunk = await cdp.send("IO.read", {"handle": stream_id})
                        buf   = (
                            base64.b64decode(chunk["data"])
                            if chunk.get("base64Encoded")
                            else chunk["data"].encode()
                        )
                        await fh.write(buf)
                        if chunk.get("eof"):
                            break
                    await cdp.send("IO.close", {"handle": stream_id})

                resources.url_to_file[url] = os.path.relpath(dest, downloads_dir.parent)
                resources.response_headers[url] = {
                    "status_code": ev.get("responseStatusCode", 200),
                    "headers": {h["name"]: h["value"] for h in hdrs},
                }
                resources.stats["downloads"] += 1
                print(f"[DOWNLOAD] Stream-saved: {dest.name}")
                
                # Validate metadata completeness
                _validate_metadata_completeness(url, resources, "CDP")
                saved = True

            except Exception as e:
                print(f"[WARN] stream save failed ({url[:MAX_URL_LOG_LENGTH]}…): {e}")

        try:
            if want:
                await cdp.send("Fetch.fulfillRequest", {
                    "requestId": req_id,
                    "responseCode": ev.get("responseStatusCode", 200),
                    "responseHeaders": hdrs,
                    "body": "",
                })
            else:
                await cdp.send("Fetch.continueResponse", {
                    "requestId": req_id,
                    "responseHeaders": hdrs,
                    "responseCode": ev.get("responseStatusCode", 200),
                })
        except CDPError as err:                        # ← updated line
            if "Invalid InterceptionId" not in str(err):
                raise
            print(f"[INFO] Request vanished before continue/fulfill – {url[:MAX_URL_LOG_LENGTH]}")


    cdp.on("Fetch.requestPaused", _on_paused)

# _make_slug moved to utils.py as make_slug

