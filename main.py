import argparse
import sys
import asyncio
from urllib.parse import urlparse
from src.map import COUNTRY_GEO, choose_ua
from src.browser import save_page

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='URL to download')
    parser.add_argument('--country', help='Country code geolocation emulation (e.g. US, UK, FR)')
    parser.add_argument('--ref', help='Referrer header')
    parser.add_argument('--ua', help='User-Agent header, e.g. Windows;;Chrome ')
    args = parser.parse_args()

    url_to_save = args.url
    gates_enabled = {}
    gate_args = {}

    # Geolocation gate
    if args.country:
        country_code = args.country
        if country_code in COUNTRY_GEO:
            gates_enabled['GeolocationGate'] = True
            gate_args['GeolocationGate'] = {'geolocation': COUNTRY_GEO[country_code]}
        else:
            print('Country code is invalid')
            sys.exit(1)
    else:
        gates_enabled['GeolocationGate'] = False

    # Referrer Gate
    if args.ref:
        gates_enabled['ReferrerGate'] = True
        gate_args['ReferrerGate'] = {'referrer': args.ref}
    else:
        gates_enabled['ReferrerGate'] = False

    if args.ua:
        gates_enabled['UserAgentGate'] = True
        ua = choose_ua(args.ua)
        gate_args['UserAgentGate'] = {'user_agent': ua}
    else:
        gates_enabled['UserAgentGate'] = False

    parsed_url = urlparse(url_to_save)
    domain = parsed_url.netloc.replace(':', '_')
    output_folder = f'./data/saved_{domain}'

    print(f'Output directory: {output_folder}')
    asyncio.run(save_page(url_to_save, output_folder, gates_enabled=gates_enabled, gate_args=gate_args))

if __name__ == '__main__':
    main()