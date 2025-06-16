import argparse
import sys
import asyncio
from urllib.parse import urlparse
from src.map import COUNTRY_GEO
from src.browser import save_page

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='URL to download')
    parser.add_argument('--country', help='Country code geolocation emulation (e.g. US, UK, FR)')
    args = parser.parse_args()

    url_to_save = args.url
    geo = None
    if args.country:
        country_code = args.country
        if country_code in COUNTRY_GEO:
            geo = COUNTRY_GEO[country_code]
        else:
            print('Country code is invalid')
            sys.exit(1)

    parsed_url = urlparse(url_to_save)
    domain = parsed_url.netloc.replace(':', '_')
    output_folder = f'./data/saved_{domain}'

    print(f'Output directory: {output_folder}')
    asyncio.run(save_page(url_to_save, output_folder, geolocation=geo))

if __name__ == '__main__':
    main()