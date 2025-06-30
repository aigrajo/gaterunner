import argparse
import sys
import asyncio
import re
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='URL to download')
    parser.add_argument('--country', help='Country code geolocation emulation (e.g. US, UK, FR)')
    parser.add_argument('--ref', help='Referrer header')
    parser.add_argument('--ua', help='User-Agent header, e.g. Windows;;Chrome ')
    parser.add_argument('--lang', help='Accept-Language header (e.g. en-US)')
    parser.add_argument('--proxy', help='SOCKS5/HTTP proxy (e.g. socks5://127.0.0.1:9050)')
    parser.add_argument('--engine', choices=["auto", "playwright", "camoufox"], default="auto",
                        help="Browser engine to use (default: auto-detect from UA)")

    args = parser.parse_args()

    # URL validation
    if not is_valid_url(args.url):
        print("[ERROR] Invalid URL. Must start with http:// or https:// and have a domain.")
        sys.exit(1)

    gates_enabled = {}
    gate_args = {}

    # Geolocation gate
    if args.country:
        country_code = args.country.upper()
        if country_code in COUNTRY_GEO:
            gates_enabled['GeolocationGate'] = True
            gate_args['GeolocationGate'] = {'geolocation': jitter_country_location(country_code)}
        else:
            print(f"[ERROR] Invalid country code: {country_code}. Must be one of {', '.join(sorted(COUNTRY_GEO))}")
            sys.exit(1)
    else:
        gates_enabled['GeolocationGate'] = False

    # Referrer gate
    if args.ref:
        gates_enabled['ReferrerGate'] = True
        gate_args['ReferrerGate'] = {'referrer': args.ref}
    else:
        gates_enabled['ReferrerGate'] = False

    # User-Agent gate
    if args.ua:
        if ';;' not in args.ua:
            print("[WARN] UA string is missing ';;' separator. This may cause fallback.")
        gates_enabled['UserAgentGate'] = True
        ua = choose_ua(args.ua)
        gate_args['UserAgentGate'] = {'user_agent': ua}
    else:
        gates_enabled['UserAgentGate'] = False

    # Language gate
    if args.lang:
        if not is_valid_lang(args.lang):
            print(f"[ERROR] Invalid language format: '{args.lang}'. Expected format like 'en-US' or 'fr'.")
            sys.exit(1)
        gates_enabled['LanguageGate'] = True
        gate_args['LanguageGate'] = {'language': args.lang}
    else:
        gates_enabled['LanguageGate'] = False

    # Proxy
    if args.proxy:
        if not is_valid_proxy(args.proxy):
            print(f"[ERROR] Invalid proxy format: {args.proxy}. Expected format: socks5://IP:PORT or http://IP:PORT")
            sys.exit(1)
        proxy = {"server": args.proxy}
    else:
        proxy = None

    # Output dir
    parsed_url = urlparse(args.url)
    domain = parsed_url.netloc.replace(':', '_')
    output_folder = f'./data/saved_{domain}'

    print(f'[INFO] Output directory: {output_folder}')
    asyncio.run(save_page(
        args.url, output_folder,
        gates_enabled=gates_enabled,
        gate_args=gate_args,
        proxy=proxy,
        engine=args.engine
    ))


if __name__ == '__main__':
    main()
