"""
html.py

Rewrites html for offline viewing
"""

import re
from bs4 import BeautifulSoup
import os

# ───────────────────────── constants ──────────────────────────

tag_attr_map: dict[str, list[str]] = {
    'img': ['src', 'srcset'],
    'script': ['src'],
    'link': ['href'],
    'iframe': ['src'],
    'audio': ['src'],
    'video': ['src', 'poster'],
    'source': ['src', 'srcset'],
    'embed': ['src'],
    'object': ['data'],
}

def rewrite_html_resources(html_content, url_to_local):
    """
    Rewrite external resource links in HTML to local file paths.

    @param html_content (str) Raw HTML content as a string.
    @param url_to_local (dict) Mapping of original URLs to local file paths.

    @return (str) Modified HTML content with updated resource links.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Update src, href, srcset attributes using tag-attribute mapping.
    for tag, attrs in tag_attr_map.items():
        for element in soup.find_all(tag):
            for attr in attrs:
                if element.has_attr(attr):
                    original = element[attr]

                    # Special handling for 'srcset' which may include multiple URLs
                    if attr == 'srcset':
                        new_srcset = []
                        for part in original.split(','):
                            url_part = part.split(' ')[0]
                            if url_part in url_to_local:
                                part = part.replace(url_part, url_to_local[url_part])
                            new_srcset.append(part)
                        element[attr] = ', '.join(new_srcset)

                    # Direct URL substitution for src, href, etc.
                    elif original in url_to_local:
                        element[attr] = url_to_local[original]

    # Rewrite inline styles with url(...) references
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
    """
    Save both original and rewritten HTML files to disk.

    @param output_dir (str) Path to output directory.
    @param html_content (str) Original HTML content.
    @param url_to_local (dict) Mapping of remote URLs to local paths for offline rewriting.

    @return (None) Writes 'page.html' and 'page_offline.html' in output_dir.
    """
    # Write raw HTML to file
    with open(os.path.join(output_dir, "page.html"), "w", encoding="utf-8") as fh:
        fh.write(html_content)

    # Rewrite resource URLs and write offline-compatible version
    offline_html = rewrite_html_resources(html_content, url_to_local)
    with open(os.path.join(output_dir, "page_offline.html"), "w", encoding="utf-8") as fh:
        fh.write(offline_html)
