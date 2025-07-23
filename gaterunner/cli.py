"""
Command-line interface for Gaterunner.

This module contains all the CLI argument parsing and main execution logic.
"""

from __future__ import annotations

import argparse, sys, asyncio, os, re, time, multiprocessing
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse

from .browser import Config
from .resources import ResourceData
from .browser import save_page
from .debug import set_verbose

BAR_LEN = 40  # characters in the progress bar

# ─── globals initialised in workers ─────────────────────────────
_GLOBAL_ARGS = None
_STATUS_DICT: Optional[Dict[int, str]] = None  # pid -> current URL (trimmed)

# ─── helper: filter noisy Playwright exceptions ─────────────────

def _loop_exception_filter(loop, context):
    exc = context.get("exception")
    if exc and isinstance(exc, Exception):
        txt = str(exc)
        if "net::ERR_ABORTED" in txt or "browser has been closed" in txt:
            return
    loop.default_exception_handler(context)

# ─── validation helpers ────────────────────────────────────────

def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def deobfuscate_url(text: str) -> str:
    return (
        text.replace("hxxp://", "http://")
        .replace("hxxps://", "https://")
        .replace("[.]", ".")
        .replace("[:]", ":")
    )

# ─── single‑URL crawler ─────────────────────────────────────────

def run_single_url_from_args(url: str, args):
    """Run single URL using command line arguments."""
    # Build configuration object using centralized method
    try:
        config = Config.from_args(args)
    except ValueError as e:
        print(f"[ERROR] {e}")
        return
    
    run_single_url(url, config)


def run_single_url(url: str, config: Config):
    """Run single URL using configuration object."""
    if not is_valid_url(url):
        print("[ERROR] Invalid URL:", url)
        return
    
    # Set debug output based on verbose flag
    set_verbose(config.verbose)
    
    # Create resource tracker
    resources = ResourceData()
    
    domain = urlparse(url).netloc.replace(":", "_")
    run_id = os.getenv("RUN_ID", "default")
    out_dir = f"{config.output_dir}/{run_id}/saved_{domain}"

    if not config.plain_progress:
        print(f"[INFO] Running Gaterunner for {url}")
        print(f"[INFO] Output directory: {out_dir}")

    async def _crawl():
        asyncio.get_running_loop().set_exception_handler(_loop_exception_filter)
        try:
            await save_page(
                url,
                out_dir,
                resources,
                config,
            )
        except asyncio.TimeoutError:
            print(f"[TIMEOUT] {url} hit {config.timeout_sec}s limit")
        except Exception as e:
            print(f"[ERROR] {url}: {e}")

    def _run():
        asyncio.run(_crawl())

    if config.interactive:
        _run()  # visible browser windows as requested
    else:
        # Invisible virtual display so the GUI has an X server but stays off‑screen
        from pyvirtualdisplay import Display
        with Display(visible=0, size=(1920, 1080)):
            _run()

# ─── display helpers ───────────────────────────────────────────

_LAST_LINE_COUNT = 0  # how many lines we wrote the last time


def _draw_screen(done: int, total: int, start_ts: float, status: Dict[int, str]):
    """Redraw progress + worker lines in place (no scrolling)."""
    global _LAST_LINE_COUNT

    for _ in range(_LAST_LINE_COUNT):
        sys.stdout.write("\033[F\033[2K")  # up one line & clear

    pct = done / total if total else 0.0
    filled = int(BAR_LEN * pct)
    bar = "#" * filled + "-" * (BAR_LEN - filled)
    elapsed = time.time() - start_ts
    header = f"[{bar}] {int(pct*100):02d}% | {int(elapsed//60):02d}:{int(elapsed%60):02d} ({done}/{total})"

    lines = [header] + [f"[W-{pid}] {url}" for pid, url in sorted(status.items())]
    _LAST_LINE_COUNT = len(lines)

    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()

# ─── multiprocessing helpers ───────────────────────────────────

def _init_pool(ns, status_dict):
    global _GLOBAL_ARGS, _STATUS_DICT
    _GLOBAL_ARGS = ns
    _STATUS_DICT = status_dict

    # Set debug flag for worker process
    set_verbose(ns.verbose)

    run_id = os.getenv("RUN_ID", "default")
    log_root = Path("./logs") / run_id
    log_root.mkdir(parents=True, exist_ok=True)
    fp = open(log_root / f"worker_{os.getpid()}.log", "a", buffering=1, encoding="utf-8", errors="replace")
    sys.stdout = fp
    sys.stderr = fp


def _worker(url_line: str):
    url = deobfuscate_url(url_line)
    pid = os.getpid()
    if _STATUS_DICT is not None:
        _STATUS_DICT[pid] = url[:80]
    try:
        run_single_url_from_args(url, _GLOBAL_ARGS)
        return True
    finally:
        if _STATUS_DICT is not None:
            _STATUS_DICT[pid] = "- idle -"

# ─── serial batch (no workers flag) ─────────────────────────────

def run_batch_serial(urls: List[str], config: Config):
    total = len(urls)
    start = time.time()
    done = 0
    for raw in urls:
        url = deobfuscate_url(raw)
        run_single_url(url, config)
        done += 1
        sys.stdout.write(f"\r[PROGRESS] {done}/{total} done\n")
        sys.stdout.flush()
    print()

# ─── main ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input",
        help="Target URL or a file path containing one URL per line",
    )

    parser.add_argument(
        "--country",
        help="ISO 3166‑1 alpha‑2 country code for geolocation spoofing (e.g. 'US', 'DE')",
    )

    parser.add_argument(
        "--ua",
        help="UA selector such as 'Windows;;Chrome' (legacy template syntax)",
    )

    parser.add_argument(
        "--ua-full",
        help="Literal User‑Agent header value; bypasses choose_ua()",
    )

    parser.add_argument(
        "--lang",
        default="en-US",
        help="Primary Accept‑Language header (e.g. 'fr-FR'); defaults to 'en-US'",
    )

    parser.add_argument(
        "--proxy",
        help="Upstream proxy URI, format socks5://host:port or http://host:port",
    )

    parser.add_argument(
        "--engine",
        choices=["auto", "playwright", "camoufox", "patchright"],
        default="auto",
        help="Browser engine: 'auto' (heuristic), 'playwright' (with stealth patches), 'camoufox' (no patches), or 'patchright' (no patches)",
    )

    parser.add_argument(
        "--headful",
        action="store_true",
        help="Launch a visible browser window instead of running through a virtual display",
    )

    parser.add_argument(
        "--timeout",
        default="30",
        help="Per‑page timeout in seconds; set higher for slow sites",
    )

    parser.add_argument(
        "--workers",
        type=int,
        help="Number of parallel worker processes (1 = serial mode)",
    )

    parser.add_argument(
        "--plain-progress",
        action="store_true",
        help="Disable ANSI progress bar; print simple line output instead",
    )

    parser.add_argument(
        "--output-dir",
        default="./data",
        help="Base directory for saving files; defaults to './data'",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug output; prints all [DEBUG] statements",
    )

    args = parser.parse_args()

    target = deobfuscate_url(args.input.strip())
    if is_valid_url(target):
        run_single_url_from_args(target, args)
        return

    if not os.path.isfile(args.input.strip()):
        print("[ERROR] Input must be a URL or file path.")
        sys.exit(1)

    with open(args.input.strip()) as f:
        urls = [ln.strip() for ln in f if ln.strip()]

    # Build configuration for batch processing
    try:
        config = Config.from_args(args)
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    # ── serial mode ────────────────────────────────────────────
    if not config.workers or config.workers < 2:
        run_batch_serial(urls, config)
        return

    # ── parallel mode ─────────────────────────────────────────
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    os.environ["RUN_ID"] = run_id

    manager = multiprocessing.Manager()
    status_dict = manager.dict()

    total = len(urls)
    start_ts = time.time()
    done = 0

    with multiprocessing.Pool(
        processes=config.workers,
        initializer=_init_pool,
        initargs=(args, status_dict),
    ) as pool:
        for _ in pool.imap_unordered(_worker, urls):
            done += 1
            if config.plain_progress:
                print(f"{done}/{total} done")
            else:
                _draw_screen(done, total, start_ts, dict(status_dict))

    if not config.plain_progress:
        print("\nRun finished. Logs in ./logs/" + run_id)