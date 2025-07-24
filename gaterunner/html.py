"""
html.py - HTML content processing for offline viewing

This module handles rewriting HTML content to use local resource references
instead of remote URLs, enabling offline browsing of captured pages.

Key functions:
- rewrite_html_resources(): Updates resource links to local paths
- save_html_files(): Saves both original and offline-compatible HTML
"""

import re
import os
from typing import Dict
from bs4 import BeautifulSoup

# ─── Constants ───────────────────────────────────────────────
# HTML tag attributes that contain resource URLs
TAG_ATTR_MAP: Dict[str, list[str]] = {
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

# Output filenames
ORIGINAL_HTML_FILENAME = "page.html"
OFFLINE_HTML_FILENAME = "page_offline.html"


def rewrite_html_resources(html_content: str, url_to_local: Dict[str, str]) -> str:
    """
    Rewrite external resource links in HTML to local file paths.

    @param html_content: Raw HTML content as a string
    @param url_to_local: Mapping of original URLs to local file paths
    @return: Modified HTML content with updated resource links
    @raises ValueError: If inputs are invalid
    """
    if not isinstance(html_content, str):
        raise ValueError("html_content must be a string")
    if not isinstance(url_to_local, dict):
        raise ValueError("url_to_local must be a dictionary")
        
    soup = BeautifulSoup(html_content, "html.parser")

    # Update src, href, srcset attributes using tag-attribute mapping.
    for tag, attrs in TAG_ATTR_MAP.items():
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


def save_html_files(output_dir: str, html_content: str, url_to_local: Dict[str, str]) -> None:
    """
    Save both original and rewritten HTML files to disk.

    @param output_dir: Path to output directory
    @param html_content: Original HTML content
    @param url_to_local: Mapping of remote URLs to local paths for offline rewriting
    @raises ValueError: If inputs are invalid
    @raises OSError: If file operations fail
    """
    if not isinstance(output_dir, str):
        raise ValueError("output_dir must be a string")
    if not isinstance(html_content, str):
        raise ValueError("html_content must be a string")
    if not isinstance(url_to_local, dict):
        raise ValueError("url_to_local must be a dictionary")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Write raw HTML to file
    original_path = os.path.join(output_dir, ORIGINAL_HTML_FILENAME)
    with open(original_path, "w", encoding="utf-8") as fh:
        fh.write(html_content)

    # Rewrite resource URLs and write offline-compatible version
    offline_html = rewrite_html_resources(html_content, url_to_local)
    offline_path = os.path.join(output_dir, OFFLINE_HTML_FILENAME)
    with open(offline_path, "w", encoding="utf-8") as fh:
        fh.write(offline_html)
