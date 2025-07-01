"""
html.py

Rewrites html for offline viewing
"""

import re
from bs4 import BeautifulSoup
import os
from .utils import tag_attr_map

def rewrite_html_resources(html_content, url_to_local):
    soup = BeautifulSoup(html_content, "html.parser")

    for tag, attrs in tag_attr_map.items():
        for element in soup.find_all(tag):
            for attr in attrs:
                if element.has_attr(attr):
                    original = element[attr]
                    if attr == 'srcset':
                        new_srcset = []
                        for part in original.split(','):
                            url_part = part.split(' ')[0]
                            if url_part in url_to_local:
                                part = part.replace(url_part, url_to_local[url_part])
                            new_srcset.append(part)
                        element[attr] = ', '.join(new_srcset)
                    elif original in url_to_local:
                        element[attr] = url_to_local[original]

    for element in soup.find_all(style=True):
        style = element['style']
        urls = re.findall(r'url\(([^)]+)\)', style)
        for url in urls:
            clean_url = url.strip('\'"')
            if clean_url in url_to_local:
                local_url = url_to_local[clean_url]
                style = style.replace(url, f'"{local_url}"')
        element['style'] = style

    return str(soup)

def save_html_files(output_dir, html_content, url_to_local):
    # Save raw HTML
    with open(os.path.join(output_dir, "page.html"), "w", encoding="utf-8") as fh:
        fh.write(html_content)

    # Rewrite resource links for offline use and save second copy
    offline_html = rewrite_html_resources(html_content, url_to_local)
    with open(os.path.join(output_dir, "page_offline.html"), "w", encoding="utf-8") as fh:
        fh.write(offline_html)