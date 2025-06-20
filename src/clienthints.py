import re
import random

# Identify brand and version
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

# Identify chromium version
def parse_chromium_version(ua):
    # Chromium version is usually in Chrome/XX.XX or Chromium/XX.XX
    m = re.search(r'(?:Chrome|Chromium)/([0-9.]+)', ua)
    if m:
        return m.group(1)
    return None

# Generate client hints string from User-Agent string
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

def parse_android_model(ua):
    # Example: 'Android 13; Pixel 7 Build/'
    m = re.search(r'Android [^;]+; ([^;]+) Build/', ua)
    if m:
        return m.group(1).strip()
    return None

def generate_sec_ch_ua_model(ua):
    model = parse_android_model(ua)
    return f'"{model}"' if model else '""'




def parse_platform_version(ua):
    if "Android" in ua:
        m = re.search(r'Android ([0-9.]+)', ua)
        if m:
            return m.group(1)
    elif "Windows NT" in ua:
        m = re.search(r'Windows NT ([0-9.]+)', ua)
        if m:
            return m.group(1)
    elif "Mac OS X" in ua:
        m = re.search(r'Mac OS X ([0-9_]+)', ua)
        if m:
            return m.group(1).replace('_', '.')
    return None

def generate_sec_ch_ua_platform_version(ua):
    version = parse_platform_version(ua)
    return f'"{version}"' if version else '""'


def parse_chromium_full_version(ua):
    # Chrome/114.0.5735.198 or Chromium/...
    m = re.search(r'(?:Chrome|Chromium)/([0-9.]+)', ua)
    if m:
        return m.group(1)
    return None

def generate_sec_ch_ua_full_version(ua):
    version = parse_chromium_full_version(ua)
    return f'"{version}"' if version else '""'

# Determine if browser wants client hints
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


