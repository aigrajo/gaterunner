import argparse, sys, asyncio, re, time, os
from urllib.parse import urlparse

from src.utils import COUNTRY_GEO, choose_ua, jitter_country_location
from src.browser import save_page

def _loop_exception_filter(loop, context):
    """
    Ignore Playwright’s stray net::ERR_ABORTED / TargetClosedError futures.
    Everything else is delegated to the default handler so real bugs stay visible.
    """
    exc = context.get("exception")
    if exc and isinstance(exc, Exception):
        txt = str(exc)
        if (
            "net::ERR_ABORTED" in txt
            or "Target page, context or browser has been closed" in txt
        ):
            return                             # swallow the noise
    loop.default_exception_handler(context)


# ─── helpers ────────────────────────────────────────────────────────
def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False

def is_valid_proxy(proxy: str) -> bool:
    return re.fullmatch(r"(socks5|http)://.+:\d{2,5}", proxy) is not None

def is_valid_lang(lang: str) -> bool:
    return re.fullmatch(r"[a-z]{2,3}(-[A-Z]{2})?$", lang) is not None

def deobfuscate_url(text: str) -> str:
    return (text.replace("hxxp://", "http://")
                .replace("hxxps://", "https://")
                .replace("[.]", ".").replace("[:]", ":"))

def run_single_url(url: str, args):
    """Crawl one URL with the requested gates / proxy / UA setup."""

    # ── basic validation ─────────────────────────────────────────
    if not is_valid_url(url):
        print("[ERROR] Invalid URL:", url)
        return

    # ── Gate switches & their arguments ─────────────────────────
    gates_enabled: dict[str, bool] = {}
    gate_args:     dict[str, dict] = {}

    if args.country:
        cc = args.country.upper()
        if cc not in COUNTRY_GEO:
            print(f"[ERROR] Invalid country code: {cc}")
            return
        gates_enabled["GeolocationGate"] = True
        gate_args["GeolocationGate"] = {"geolocation": jitter_country_location(cc)}

    if args.lang:
        if not is_valid_lang(args.lang):
            print(f"[ERROR] Invalid language: {args.lang}")
            return
        gates_enabled["LanguageGate"] = True
        gate_args["LanguageGate"] = {"language": args.lang}

    if args.ua:
        gates_enabled["UserAgentGate"] = True
        gate_args["UserAgentGate"] = {
            "user_agent": choose_ua(args.ua),
            "ua_arg":     args.ua,
        }

    # ── proxy parsing ───────────────────────────────────────────
    proxy = {"server": args.proxy} if args.proxy and is_valid_proxy(args.proxy) else None
    if args.proxy and not proxy:
        print("[ERROR] Invalid proxy format.")
        return

    # ── housekeeping paths & flags ─────────────────────────────
    domain  = urlparse(url).netloc.replace(":", "_")
    out_dir = f"./data/saved_{domain}"
    timeout = int(args.timeout)
    print(f"[INFO] Output directory: {out_dir}")

    interactive     = args.headful          # real window when --headful
    launch_headless = False                 # always launch with GUI bits (realism)

    # ── async crawl wrapper – installs loop-level exception filter ──
    async def _crawl():
        asyncio.get_running_loop().set_exception_handler(_loop_exception_filter)

        await save_page(
            url,
            out_dir,
            gates_enabled=gates_enabled,
            gate_args=gate_args,
            proxy=proxy,
            engine=args.engine,
            launch_headless=launch_headless,
            interactive=interactive,
            timeout_sec=timeout,
        )

    # ── synchronous helper to enter the async world ────────────
    def _run():
        asyncio.run(_crawl())

    # ── headful vs. headless (Xvfb) branch ─────────────────────
    if interactive:              # user asked for a visible browser window
        _run()
        return

    from pyvirtualdisplay import Display  # Xvfb for headless
    with Display(visible=0, size=(1920, 1080)):
        _run()


# ─── batch wrapper & CLI ───────────────────────────────────────────
def run_batch(urls, args):
    total = len(urls)
    start_time = time.time()

    for count, raw_url in enumerate(urls, 1):
        url = deobfuscate_url(raw_url.strip())

        percent = int(100 * count / total)
        elapsed = time.time() - start_time
        elapsed_fmt = f"{int(elapsed//60):02d}m:{int(elapsed%60):02d}s"

        print(f"[*] Running gatekey for: {url}")
        print(f"[*] Progress: {count}/{total} ({percent}%) | Elapsed: {elapsed_fmt}")

        try:
            run_single_url(url, args)
        except (asyncio.TimeoutError, asyncio.CancelledError) as exc:
            print(f"[TIMEOUT] Skipped {url}: {exc}")
        except Exception as exc:
            print(f"[ERROR] {url} failed: {type(exc).__name__}: {exc}")

    total_elapsed = time.time() - start_time
    print(f"[*] Done. Total time: {int(total_elapsed//60):02d}m:{int(total_elapsed%60):02d}s")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("input", help="URL or file with URLs")
    p.add_argument("--country")
    p.add_argument("--ua")
    p.add_argument("--lang", default="en-US")
    p.add_argument("--proxy")
    p.add_argument("--engine",
                   choices=["auto", "playwright", "camoufox", "patchright"],
                   default="auto")
    p.add_argument("--headful", action="store_true",
                   help="Show real window; omit for invisible Xvfb.")
    p.add_argument("--timeout", default="30")
    args = p.parse_args()

    target = deobfuscate_url(args.input.strip())
    if is_valid_url(target):
        run_single_url(target, args)
    elif os.path.isfile(args.input.strip()):
        with open(args.input.strip()) as f:
            run_batch(f.readlines(), args)
    else:
        print("[ERROR] Input must be a URL or file path.")
        sys.exit(1)

if __name__ == "__main__":
    main()
