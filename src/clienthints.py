import re
import random
from ua_parser import user_agent_parser

ARCH_PATTERNS = [
    # key substrings -> (architecture, bitness, wow64 flag)
    (('wow64',),          ('x86', '32', True)),
    (('amd64', 'x86_64', 'win64', 'x64', 'ia64'),
                         ('x86', '64', False)),
    (('i686', 'i386', 'x86'), ('x86', '32', False)),
    (('arm64', 'aarch64', 'armv8'), ('arm', '64', False)),
    (('armv7', 'armv6', 'arm;'),    ('arm', '32', False)),
]

def _detect_arch(ua_lower: str):
    for needles, out in ARCH_PATTERNS:
        if any(n in ua_lower for n in needles):
            return out
    return ('', '', False)          # unknown

def _detect_model(ua: str):
    # Android (try Build/… first, then relaxed pattern)
    m = re.search(r'Android [\d.]+; ([^;/\)]+) Build/', ua)
    if not m:
        m = re.search(r'Android [\d.]+; ([^;\)]+)', ua)
    if m:
        return m.group(1).strip()

    # iOS
    m = re.search(r'\((iP(?:hone|ad|od)[^;)]*)', ua)
    return m.group(1).strip() if m else ''

def _detect_platform(parsed_os):
    family = parsed_os['family']
    mapping = {
        ('Windows', 'Windows NT'): 'Windows',
        ('Mac OS X', 'Mac OS'):    'macOS',
        ('Chrome OS',):            'Chrome OS',
        ('Android',):              'Android',
        ('iOS', 'iPhone OS'):      'iOS',
        ('KaiOS',):               'KaiOS',
        ('Linux',):                'Linux',
    }
    for keys, value in mapping.items():
        if family in keys:
            return value
    return family or ''

def _detect_platform_version(platform, ua):
    rx = {
        'Windows':   r'Windows NT ([\d.]+)',
        'macOS':     r'Mac OS X ([\d_]+)',
        'Android':   r'Android ([\d.]+)',
        'iOS':       r'OS ([\d_]+)',
        'Chrome OS': r'CrOS [^ ]+ ([\d.]+)',
        'KaiOS':     r'KAIOS/([\d.]+)',
    }.get(platform)
    if rx:
        m = re.search(rx, ua)
        if m:
            return m.group(1).replace('_', '.')
    return ''

def extract_high_entropy_hints(ua_string: str) -> dict:
    ua_lower = ua_string.lower()
    parsed   = user_agent_parser.Parse(ua_string)

    architecture, bitness, wow64 = _detect_arch(ua_lower)
    model            = _detect_model(ua_string)
    platform         = _detect_platform(parsed['os'])
    platform_version = _detect_platform_version(platform, ua_string)

    return {
        'architecture'   : architecture,
        'bitness'        : bitness,
        'wow64'          : wow64,
        'model'          : model,
        'platform'       : platform,
        'platformVersion': platform_version,
    }


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


