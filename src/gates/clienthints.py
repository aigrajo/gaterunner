import re
import random

def parse_chromium_ua(ua):
    # Patterns for common Chromium-based browsers
    patterns = [
        (r'EdgA?/([0-9.]+)', 'Microsoft Edge'),
        (r'OPR/([0-9.]+)', 'Opera'),
        (r'YaBrowser/([0-9.]+)', 'Yandex'),
        (r'Brave/([0-9.]+)', 'Brave'),
        (r'Chrome/([0-9.]+)', 'Google Chrome'),
        (r'Chromium/([0-9.]+)', 'Chromium'),
        (r'QQBrowser/([0-9.]+)', 'QQBrowser'),
        (r'UCBrowser/([0-9.]+)', 'UC Browser'),
        # Add more as needed
    ]
    for pattern, brand in patterns:
        m = re.search(pattern, ua)
        if m:
            version = m.group(1)
            return brand, version
    return None, None

def parse_chromium_version(ua):
    # Chromium version is usually in Chrome/XX.XX or Chromium/XX.XX
    m = re.search(r'(?:Chrome|Chromium)/([0-9.]+)', ua)
    if m:
        return m.group(1)
    return None

def generate_sec_ch_ua(ua):
    brand, brand_version = parse_chromium_ua(ua)
    chromium_version = parse_chromium_version(ua)
    if not brand or not brand_version or not chromium_version:
        raise ValueError("Not a recognized Chromium-based UA string")

    # Compose brands
    brands = [
        ('Chromium', chromium_version.split('.')[0]),
        ('Not-A.Brand', '99'),
        (brand, brand_version.split('.')[0])
    ]

    # Remove duplicate brands (e.g., "Chromium" and "Google Chrome" for Chrome)
    unique_brands = []
    seen = set()
    for b, v in brands:
        if b not in seen:
            unique_brands.append((b, v))
            seen.add(b)

    # GREASE: randomize order
    random.shuffle(unique_brands)

    # Format as sec-ch-ua string
    sec_ch_ua = ', '.join(f'"{b}";v="{v}"' for b, v in unique_brands)
    return sec_ch_ua

def send_ch(ua):
    ua = ua.lower()

    # Always NO for Firefox and Safari
    if 'firefox' in ua or 'safari' in ua and 'ucbrowser' in ua and 'chrome' not in ua and 'chromium' not in ua:
        return False

    # Chrome, Edge, Opera, Brave, Yandex, MIUI, QQBrowser, UC Browser (Chromium-based)
    chromium_browsers = [
        (r'chrome/(\d+)', 89),
        (r'crios/(\d+)', 89),  # Chrome on iOS
        (r'edg[a]?/(\d+)', 90),  # Edge
        (r'opr/(\d+)', 75),  # Opera
        (r'yabrowser/(\d+)', 1),  # Yandex
        (r'miui browser/(\d+)', 1),  # MIUI Browser (Chromium-based from v13)
        (r'qqbrowser/(\d+)', 10),  # QQBrowser (Chromium-based from v10)
        (r'android.*version/(\d+).*chrome', 84),  # Android Browser (Chromium-based)
    ]

    for pattern, min_version in chromium_browsers:
        m = re.search(pattern, ua)
        if m:
            try:
                version = int(m.group(1))
                if version >= min_version:
                    return True
                else:
                    return False
            except ValueError:
                continue

    # If not matched, do not send sec-ch-ua
    return False


