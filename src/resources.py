"""
resources.py – save network responses and metadata
"""


import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import Error

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

_BINARY_MIME_SNIPPETS: tuple[str, ...] = (
    "application/pdf",
    "application/zip",
    "application/x-msdownload",
    "application/vnd.microsoft.portable-executable",
    "application/octet-stream",
)

# ───────────────────────── helpers ──────────────────────────

def _guess_ext(ct: str) -> str:
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
    """Return *stem* + '_' + 8‑hex‑md5 + *ext*, trimming *stem* when needed."""
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
    if not cd:
        return None
    m = _FILENAME_RE.search(cd)
    if not m:
        return None
    raw_name = m.group("name").strip("\"'")
    stem, ext = os.path.splitext(os.path.basename(raw_name))
    return _safe_filename(stem or "download", ext, raw_name)


def _fname_from_url(url: str, fallback_ext: str) -> str:
    path = urlparse(url).path
    stem, ext = os.path.splitext(os.path.basename(path) or "index")
    if not ext and fallback_ext:
        ext = fallback_ext
    return _safe_filename(stem, ext, url)


def _looks_like_download(ct: str, cd: str | None) -> bool:
    if cd and "attachment" in cd.lower():
        return True
    ct_low = ct.lower()
    return any(snippet in ct_low for snippet in _BINARY_MIME_SNIPPETS)

# ───────────────────────── hooks ──────────────────────────

async def handle_request(request, res_urls: set[str]):
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
    req_type = response.request.resource_type
    if req_type not in {
        "document", "stylesheet", "script", "image", "font", "media", "other",
    }:
        return

    url = response.url
    resp_hdrs[url] = {
        "status_code": response.status,
        "headers": dict(response.headers),
    }

    # ignore redirects – we only log final resources
    if 300 <= response.status < 400:
        return

    ct = response.headers.get("content-type", "") or ""
    cd = response.headers.get("content-disposition", "")
    ext = _guess_ext(ct) or os.path.splitext(urlparse(url).path)[1]
    fname = _fname_from_cd(cd) or _fname_from_url(url, ext)

    # decide output directory
    is_download = _looks_like_download(ct, cd)
    if is_download:
        dirpath = os.path.join(out_dir, "downloads")
    else:
        subdir = RESOURCE_DIRS.get(req_type, "other")
        dirpath = os.path.join(out_dir, subdir) if subdir else out_dir
    os.makedirs(dirpath, exist_ok=True)

    fpath = os.path.join(dirpath, fname)
    url_map[url] = os.path.relpath(fpath, out_dir)

    try:
        body = await response.body()
        if not body:
            return
        with open(fpath, "wb") as fh:
            fh.write(body)
        if is_download:
            stats["downloads"] += 1
            print(f"[DOWNLOAD] Saved: {fname}")
    except Error as e:
        # common when the resource was blocked / CORS etc.
        if "Network.getResponseBody" in str(e):
            print(f"[WARN] Body unavailable: {url}")
            return
        print(f"[ERROR] Could not save {url}: {e}")
        stats["errors"] += 1
    except OSError as e:
        # File still too long / invalid after sanitising – warn but keep going.
        print(f"[WARN] Could not write {fname}: {e}")
        stats["warnings"] += 1

# ───────────────────────── misc helpers ──────────────────────────

def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


async def save_screenshot(page, out_dir: str):
    try:
        await page.screenshot(path=f"{out_dir}/screenshot.png", full_page=True)
    except Exception:
        print("[WARN] screenshot failed (page closed)")
