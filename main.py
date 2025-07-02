import argparse
import sys
import asyncio
import re
import time
import os
from urllib.parse import urlparse

from src.utils import COUNTRY_GEO, choose_ua, jitter_country_location
from src.browser import save_page


def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def is_valid_proxy(proxy: str) -> bool:
    return re.match(r"^(socks5|http)://\d{1,3}(\.\d{1,3}){3}:\d{2,5}$", proxy) is not None


def is_valid_lang(lang: str) -> bool:
    return re.match(r"^[a-z]{2,3}(-[A-Z]{2})?$", lang) is not None


def deobfuscate_url(obf_url: str) -> str:
    # Common CTI-style obfuscations
    return (
        obf_url
        .replace("hxxp://", "http://")
        .replace("hxxps://", "https://")
        .replace("[.]", ".")
        .replace("[:]", ":")
    )

def run_single_url(url, args):
    if not is_valid_url(url):
        print("[ERROR] Invalid URL:", url)
        return

    gates_enabled = {}
    gate_args = {}

    if args.country:
        country_code = args.country.upper()
        if country_code in COUNTRY_GEO:
            gates_enabled['GeolocationGate'] = True
            gate_args['GeolocationGate'] = {'geolocation': jitter_country_location(country_code)}
        else:
            print(f"[ERROR] Invalid country code: {country_code}. Must be one of {', '.join(sorted(COUNTRY_GEO))}")
            return
    else:
        gates_enabled['GeolocationGate'] = False

    if args.ref:
        if is_valid_url(args.ref):
            gates_enabled['ReferrerGate'] = True
            gate_args['ReferrerGate'] = {'referrer': args.ref}
        else:
            print("[ERROR] Invalid referrer URL.")
            return
    else:
        gates_enabled['ReferrerGate'] = False

    if args.ua:
        if ';;' not in args.ua:
            print("[WARN] UA string is missing ';;'. Falling back to default.")
        gates_enabled['UserAgentGate'] = True
        ua = choose_ua(args.ua)
        gate_args['UserAgentGate'] = {'user_agent': ua, 'ua_arg': args.ua}
    else:
        gates_enabled['UserAgentGate'] = False

    if args.lang:
        if not is_valid_lang(args.lang):
            print(f"[ERROR] Invalid language: {args.lang}. Use format like en-US.")
            return
        gates_enabled['LanguageGate'] = True
        gate_args['LanguageGate'] = {'language': args.lang}
    else:
        gates_enabled['LanguageGate'] = False

    proxy = {"server": args.proxy} if args.proxy and is_valid_proxy(args.proxy) else None
    if args.proxy and not proxy:
        print("[ERROR] Invalid proxy format.")
        return

    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace(':', '_')
    output_folder = f'./data/saved_{domain}'
    timeout = int(args.timeout)

    print(f'[INFO] Output directory: {output_folder}')
    asyncio.run(save_page(
        url, output_folder,
        gates_enabled=gates_enabled,
        gate_args=gate_args,
        proxy=proxy,
        engine=args.engine,
        headless=not args.headful,
        timeout_sec=timeout
    ))


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

        run_single_url(url, args)

    total_elapsed = time.time() - start_time
    print(f"[*] Done. Total time: {int(total_elapsed//60):02d}m:{int(total_elapsed%60):02d}s")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='A single URL or path to a file of URLs (obfuscated format OK)')

    parser.add_argument('--country', help='Country code geolocation emulation')
    parser.add_argument('--ref', help='Referrer header')
    parser.add_argument('--ua', help='User-Agent header')
    parser.add_argument('--lang', default="en-US", help='Accept-Language header, default is \'en-US\'')
    parser.add_argument('--proxy', help='send through SOCKS5/HTTP proxy')
    parser.add_argument('--engine', choices=["auto", "playwright", "camoufox"], default="auto", help="specifically for using playwright's firefox instead of defaulting to camoufox")
    parser.add_argument('--headful', action='store_true', help='Use non-headless browser mode')
    parser.add_argument('--timeout', default="30", help='Timeout in seconds. Default is 30 seconds')

    args = parser.parse_args()
    input_arg = deobfuscate_url(args.input.strip())

    if is_valid_url(input_arg):
        run_single_url(input_arg, args)
    elif os.path.isfile(args.input.strip()):
        with open(args.input.strip()) as f:
            urls = f.readlines()
        run_batch(urls, args)
    else:
        print("[ERROR] Input must be a valid URL or a file path.")
        sys.exit(1)


if __name__ == '__main__':
    main()
