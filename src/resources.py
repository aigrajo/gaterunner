"""
resources.py – save network responses and metadata
"""


import hashlib
import json
import os
import re
import urllib
from pathlib import Path
from urllib.parse import urlparse
import httpx, aiofiles
from httpx import HTTPStatusError

from playwright.async_api import Error
from playwright._impl._errors import Error as CDPError

from .utils import RESOURCE_DIRS

# ───────────────────────── constants ──────────────────────────

# Leave a little slack for parent‑dir prefix when computing max length.
_MAX_FILENAME_LEN = 240  # 255 is the usual hard limit on most POSIX filesystems.

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


def _safe_filename(stem: str, ext: str, salt: str) -> str:
    """Return *stem* + '_' + 8‑hex‑md5 + *ext*, trimming *stem* if needed.

    @param stem (str): Base filename without extension.
    @param ext (str): File extension, including leading dot.
    @param salt (str): Salt value used to generate deterministic MD5 suffix.

    @return (str): Sanitized filename safe for saving to disk.
    """

    salt = hashlib.md5(salt.encode()).hexdigest()[:8]
    # room for underscore between stem and salt
    budget = _MAX_FILENAME_LEN - len(ext) - len(salt) - 1
    if budget < 8:
        # pathological: give up on the stem entirely.
        return f"{salt}{ext}"
    if len(stem) > budget:
        stem = stem[:budget]
    return f"{stem}_{salt}{ext}"


def _fname_from_cd(cd: str | None) -> str | None:
    """Extract filename from Content-Disposition header.

    @param cd (str | None): The Content-Disposition header value.

    @return (str | None): Filename if extractable. None if not present or invalid.
    """

    if not cd:
        return None

    # 1 RFC 5987 path: filename*=
    m = _FILENAME_STAR_RE.search(cd)
    if m:
        raw = urllib.parse.unquote(m["enc"])
        stem, ext = os.path.splitext(os.path.basename(raw))
        return _safe_filename(stem or "download", ext, raw)

    # 2 Legacy path: filename=
    m = _FILENAME_RE.search(cd)
    if m:
        raw_name = m.group("name").strip("\"'")
        stem, ext = os.path.splitext(os.path.basename(raw_name))
        return _safe_filename(stem or "download", ext, raw_name)

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
    return _safe_filename(stem, ext, url)


def _looks_like_download(ct: str, cd: str | None) -> bool:
    """Check if response looks like a file download.

    @param ct (str): Content-Type header.
    @param cd (str | None): Content-Disposition header.

    @return (bool): True if it's likely a file download. False otherwise.
    """

    cd_low = (cd or "").lower()
    if "attachment" in cd_low or "filename=" in cd_low:
        return True

    ct_low = ct.lower()
    return any(snippet in ct_low for snippet in _BINARY_MIME_SNIPPETS)

# ───────────────────────── hooks ──────────────────────────

async def handle_request(request, res_urls: set[str]):
    """Track network requests for static resources.

    @param request (playwright.Request): The intercepted network request object.
    @param res_urls (set[str]): A set to collect the URLs of requested resources.

    @return None
    """

    if request.resource_type in {
        "document", "stylesheet", "script", "image", "font", "media", "other",
    }:
        print(f"[RESOURCE] {request.resource_type.upper()}: {request.url}")
        res_urls.add(request.url)


async def handle_response(
    response,
    out_dir: str,
    url_map: dict[str, str],
    resp_hdrs: dict[str, dict],
    stats: dict,
):
    """Save qualifying network responses to disk and update metadata.

    @param response (playwright.Response): The intercepted network response.
    @param out_dir (str): Path to the output directory for saved resources.
    @param url_map (dict[str, str]): Maps each URL to its saved relative file path.
    @param resp_hdrs (dict[str, dict]): Stores response status and headers by URL.
    @param stats (dict): Collects counters like "downloads", "errors", "warnings".

    @return None
    """

    if response.url in url_map:  # already saved by interceptor
        return

    req_type = response.request.resource_type
    if req_type not in {
        "document", "stylesheet", "script", "image",
        "font", "media", "xhr", "fetch", "other",
    }:
        return

    url = response.url
    resp_hdrs[url] = {
        "status_code": response.status,
        "headers": dict(response.headers),
    }

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

    fpath = _dedup(Path(dirpath) / fname)
    url_map[url] = os.path.relpath(fpath, out_dir)

    try:
        body = await response.body()
        if not body:
            raise Error("empty")
        fpath.write_bytes(body)
        if is_download:
            stats["downloads"] += 1
            print(f"[DOWNLOAD] Saved: {fpath.name}")

    except Error as e:
        if any(tok in str(e) for tok in ("Network.getResponseBody", "empty")):
            success = await _stream_fetch(response.request, fpath)
            if success:
                if is_download:
                    stats["downloads"] += 1
                print(f"[DOWNLOAD] Fetched via HTTP: {fpath.name}")
            else:
                stats["errors"] += 1
                print(f"[ERROR] Fallback fetch failed for {url[:80]}…")
            return
        stats["errors"] += 1
        print(f"[ERROR] Could not save {url}: {e}")

    except OSError as e:
        stats["warnings"] += 1
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

async def _stream_fetch(req, dest: Path, timeout: int = 30):
    """Replay the original request outside DevTools, keeping method, body, cookies."""
    url = req.url
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
                async for chunk in r.aiter_bytes(65536):
                    await fh.write(chunk)
        return True
    except (HTTPStatusError, httpx.TransportError):
        return False

def _dedup(path: Path) -> Path:
    """Avoid clobbering when a name repeats in one crawl session."""
    counter = 1
    stem, ext = path.stem, path.suffix
    while path.exists():
        path = path.with_name(f"{stem}_{counter}{ext}")
        counter += 1
    return path

async def enable_cdp_download_interceptor(
    page,
    downloads_dir,
    url_map: dict[str, str],
    resp_hdrs: dict[str, dict],
    stats: dict,
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
                dest  = _dedup(downloads_dir / fname)
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

                url_map[url] = os.path.relpath(dest, downloads_dir.parent)
                resp_hdrs[url] = {
                    "status_code": ev.get("responseStatusCode", 200),
                    "headers": {h["name"]: h["value"] for h in hdrs},
                }
                stats["downloads"] += 1
                print(f"[DOWNLOAD] Stream-saved: {dest.name}")
                saved = True

            except Exception as e:
                print(f"[WARN] stream save failed ({url[:80]}…): {e}")

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
            print(f"[INFO] Request vanished before continue/fulfill – {url[:80]}")


    cdp.on("Fetch.requestPaused", _on_paused)

_MAX_SLUG_LEN = 80

def _make_slug(netloc: str, path: str, max_len: int = _MAX_SLUG_LEN) -> str:
    raw = f"{netloc}_{path}".rstrip("_")
    tail = hashlib.md5(raw.encode()).hexdigest()[:8]   # 8-char hash keeps slugs unique
    if len(raw) > max_len:
        raw = raw[:max_len]
    return f"{raw}_{tail}"

