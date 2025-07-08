import argparse, sys, asyncio, re, time, os
from urllib.parse import urlparse

from src.utils import COUNTRY_GEO, choose_ua, jitter_country_location
from src.browser import save_page

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

# ─── single URL runner ─────────────────────────────────────────────
def run_single_url(url: str, args):
    if not is_valid_url(url):
        print("[ERROR] Invalid URL:", url); return

    gates_enabled, gate_args = {}, {}

    # geo, language, UA … (unchanged logic)
    if args.country:
        cc = args.country.upper()
        if cc not in COUNTRY_GEO:
            print(f"[ERROR] Invalid country code: {cc}"); return
        gates_enabled["GeolocationGate"] = True
        gate_args["GeolocationGate"] = {"geolocation": jitter_country_location(cc)}

    if args.lang:
        if not is_valid_lang(args.lang):
            print(f"[ERROR] Invalid language: {args.lang}"); return
        gates_enabled["LanguageGate"] = True
        gate_args["LanguageGate"] = {"language": args.lang}

    if args.ua:
        gates_enabled["UserAgentGate"] = True
        gate_args["UserAgentGate"] = {
            "user_agent": choose_ua(args.ua),
            "ua_arg":     args.ua
        }

    proxy = {"server": args.proxy} if args.proxy and is_valid_proxy(args.proxy) else None
    if args.proxy and not proxy:
        print("[ERROR] Invalid proxy format."); return

    domain = urlparse(url).netloc.replace(":", "_")
    out_dir = f"./data/saved_{domain}"
    timeout = int(args.timeout)
    print(f"[INFO] Output directory: {out_dir}")

    # ─── display plan ───
    interactive = args.headful               # True ⇢ real window
    use_virtual = not interactive            # False ⇢ no Xvfb
    launch_headless = False                  # always run “headed” for FP realism

    if use_virtual:
        try:
            from pyvirtualdisplay import Display
        except ImportError:
            print("[ERROR] Install pyvirtualdisplay for hidden mode."); return
        with Display(visible=0, size=(1920, 1080)):
            asyncio.run(save_page(
                url, out_dir,
                gates_enabled=gates_enabled,
                gate_args=gate_args,
                proxy=proxy,
                engine=args.engine,
                launch_headless=launch_headless,
                interactive=interactive,
                timeout_sec=timeout
            ))
    else:
        asyncio.run(save_page(
            url, out_dir,
            gates_enabled=gates_enabled,
            gate_args=gate_args,
            proxy=proxy,
            engine=args.engine,
            launch_headless=launch_headless,
            interactive=interactive,
            timeout_sec=timeout
        ))

# ─── batch wrapper & CLI ───────────────────────────────────────────
def run_batch(urls, args):
    start = time.time()
    for idx, raw in enumerate(urls, 1):
        url = deobfuscate_url(raw.strip())
        print(f"\n[{idx}/{len(urls)}] {url}")
        run_single_url(url, args)
    print(f"\n[INFO] Finished in {time.time() - start:.1f} s")

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
