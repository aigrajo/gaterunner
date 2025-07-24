"""
Command-line interface for Gaterunner.

This module contains all the CLI argument parsing and main execution logic.
"""

from __future__ import annotations

import argparse
import asyncio
import multiprocessing
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from .browser import Config, save_page, DEFAULT_TIMEOUT_SEC, DEFAULT_OUTPUT_DIR, DEFAULT_LANGUAGE
from .debug import set_verbose
from .resources import ResourceData

# ─── Constants ───────────────────────────────────────────────
BAR_LEN = 40  # characters in the progress bar
MAX_WORKER_LOG_LINES = 1000  # prevent memory bloat in long runs

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

# ─── argument parsing helpers ───────────────────────────────

def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the command line argument parser."""
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
        default=DEFAULT_LANGUAGE,
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
        default=str(DEFAULT_TIMEOUT_SEC),
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
        default=DEFAULT_OUTPUT_DIR,
        help="Base directory for saving files; defaults to './data'",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug output; prints all [DEBUG] statements",
    )
    
    return parser


def process_input_target(input_arg: str) -> tuple[bool, str | List[str]]:
    """
    Process the input argument to determine if it's a URL or file with URLs.
    
    @param input_arg: Input argument from command line
    @return: Tuple of (is_single_url, url_or_url_list)
    """
    target = deobfuscate_url(input_arg.strip())
    
    if is_valid_url(target):
        return True, target
    
    if not os.path.isfile(input_arg.strip()):
        print("[ERROR] Input must be a URL or file path.")
        sys.exit(1)

    with open(input_arg.strip()) as f:
        urls = [ln.strip() for ln in f if ln.strip()]
    
    return False, urls


def setup_parallel_processing(config: Config) -> str:
    """
    Set up environment for parallel processing.
    
    @param config: Configuration object
    @return: Run ID for logging
    """
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    os.environ["RUN_ID"] = run_id
    return run_id

def main():
    """Main entry point for the Gaterunner CLI."""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Process input to determine if single URL or batch
    is_single_url, target_data = process_input_target(args.input)
    
    if is_single_url:
        # Single URL processing
        run_single_url_from_args(target_data, args)
        return

    # Batch processing
    urls = target_data
    
    # Build configuration for batch processing
    try:
        config = Config.from_args(args)
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    # Choose processing mode
    if not config.workers or config.workers < 2:
        # Serial mode
        run_batch_serial(urls, config)
        return

    # Parallel mode
    run_id = setup_parallel_processing(config)
    
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