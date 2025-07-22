"""
clienthints.py

Short library of client hint and high-entropy generation functions.
Pass a user agent string -> get a client hint value

Also contains consolidated UA parsing utilities used across the project.
"""

import re
import random
from ua_parser import user_agent_parser

# ──────────────────────────────
# Optional: httpagentparser for robust engine detection
# ──────────────────────────────
try:
    import httpagentparser  # type: ignore
    _HAS_HTTPAGENT = True
except ImportError:  # library not installed – fallback to simple rules
    _HAS_HTTPAGENT = False

# ──────────────────────────────
# Consolidated UA Detection Functions
# ──────────────────────────────

def detect_os_family(ua: str) -> str:
    """
    Detect OS family from user agent string.
    
    Consolidated function (was duplicated in context.py and webgl.py).
    
    @param ua: User agent string
    @return: OS family name ("windows", "mac", "android", "ios", "chromeos", "linux")
    """
    low = ua.lower()
    if "windows" in low:
        return "windows"
    if "mac os" in low or "macos" in low:
        return "mac"
    if "android" in low:
        return "android"
    if any(tok in low for tok in ("iphone", "ipad", "ios")):
        return "ios"
    if "cros" in low or "chrome os" in low:
        return "chromeos"
    return "linux"


def detect_engine_from_ua(ua: str) -> str:
    """
    Detect browser engine from user agent string.
    
    Consolidated function that reuses the logic from send_ch() but returns engine names.
    
    @param ua: User agent string
    @return: Engine name ("chromium", "firefox", "webkit")
    """
    if _HAS_HTTPAGENT:
        try:
            parsed = httpagentparser.detect(ua)  # type: ignore
            browser = (parsed.get("browser") or {})
            name = (browser.get("name") or "").lower()
            if "firefox" in name:
                return "firefox"
            if "safari" in name and "chrome" not in name:
                return "webkit"
            return "chromium"
        except Exception:
            pass  # Fall through to simple heuristics
    
    # Reuse logic from send_ch() function for consistency
    ua_lower = ua.lower()
    
    # Explicitly check for Firefox (same logic as send_ch)
    if 'firefox' in ua_lower and 'seamonkey' not in ua_lower:
        return "firefox"
    
    # Check for Safari (same logic as send_ch)
    if 'safari' in ua_lower and 'chrome' not in ua_lower and 'chromium' not in ua_lower:
        return "webkit"
    
    # Everything else is considered Chromium-based (same as send_ch default)
    return "chromium"


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
    """
    Match UA string against known CPU architecture indicators.

    @param ua_lower (str) Lowercased user-agent string to search for architecture hints.

    @return (tuple) A tuple: (arch_name, arch_bits, is_mobile)
      - arch_name (str): CPU architecture name if matched (e.g. 'x86', 'arm').
      - arch_bits (str): Architecture bit width as string (e.g. '64', '32').
      - is_mobile (bool): True if architecture is typically used on mobile devices.
    """
    for needles, out in ARCH_PATTERNS:
        if any(n in ua_lower for n in needles):
            return out
    return '', '', False  # unknown

def _detect_model(ua: str):
    """
    Extract device model name from user-agent string if possible.

    @param ua (str) Full user-agent string to extract model information from.

    @return (str) Model name if matched. Returns empty string if no match found.
    """
    # Android devices: match model from "Build/" pattern first.
    m = re.search(r'Android [\d.]+; ([^;/)]+) Build/', ua)
    if not m:
        # Fallback: relaxed Android pattern.
        m = re.search(r'Android [\d.]+; ([^;)]+)', ua)
    if m:
        return m.group(1).strip()

    # iOS devices: extract model string from parenthesis block.
    m = re.search(r'\((iP(?:hone|ad|od)[^;)]*)', ua)
    return m.group(1).strip() if m else ''

def _detect_platform(parsed_os):
    """
    Normalize parsed OS family name to a standard platform label.

    @param parsed_os (dict) Dictionary from user_agent_parser.Parse()['os'].
      Must contain key 'family'.

    @return (str) Standardized platform name, such as:
      - 'Windows', 'macOS', 'Android', 'iOS', etc.
      Returns original family name or empty string if no match.
    """
    family = parsed_os['family']

    mapping = {
        ('Windows', 'Windows NT'): 'Windows',
        ('Mac OS X', 'Mac OS'): 'macOS',
        ('Chrome OS',): 'Chrome OS',
        ('Android',): 'Android',
        ('iOS', 'iPhone OS'): 'iOS',
        ('KaiOS',): 'KaiOS',
        ('Linux',): 'Linux',
    }

    for keys, value in mapping.items():
        if family in keys:
            return value

    return family or ''


def _detect_platform_version(platform, ua):
    """
    Extract OS version string from user-agent based on known platform label.

    @param platform (str) Normalized platform name (e.g. 'Windows', 'iOS', 'Android').
    @param ua (str) Full user-agent string.

    @return (str) Extracted version string (e.g. '10.0', '16.6.1'), or empty string if no match.
    """
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
    """
    Generate high-entropy client hint values from a user-agent string.

    @param ua_string (str) Full user-agent string from the HTTP request.

    @return (dict) Dictionary of high-entropy hints:
      - 'architecture' (str): CPU architecture name (e.g. 'x86', 'arm').
      - 'bitness' (str): CPU bit width (e.g. '64').
      - 'wow64' (bool): True if 32-bit process on 64-bit Windows.
      - 'model' (str): Device model string (usually Android or iOS).
      - 'platform' (str): Normalized platform name.
      - 'platformVersion' (str): OS version string with dot-separated format.
    """
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



def parse_chromium_ua(ua):
    """
    Identify Chromium-based browser brand and version from user-agent string.

    @param ua (str) Full user-agent string.

    @return (tuple) (brand, version)
      - brand (str): Browser name (e.g. 'Google Chrome', 'Brave').
      - version (str): Version string (e.g. '124.0.6367.60').
      Returns (None, None) if no known pattern matched.
    """
    # Patterns for common Chromium-based browsers.
    patterns = [
        (r'EdgA?/([0-9.]+)', 'Microsoft Edge'),
        (r'OPR/([0-9.]+)', 'Opera'),
        (r'YaBrowser/([0-9.]+)', 'Yandex'),
        (r'Brave/([0-9.]+)', 'Brave'),
        (r'Chrome/([0-9.]+)', 'Google Chrome'),
        (r'Chromium/([0-9.]+)', 'Chromium'),
        (r'QQBrowser/([0-9.]+)', 'QQBrowser'),
        (r'UCBrowser/([0-9.]+)', 'UC Browser'),
        # Extend with other Chromium forks as needed.
    ]

    for pattern, brand in patterns:
        m = re.search(pattern, ua)
        if m:
            version = m.group(1)
            return brand, version

    return None, None


def parse_chromium_version(ua):
    """
    Extract the Chromium engine version from the user-agent string.

    @param ua (str) Full user-agent string.

    @return (str or None) Version string (e.g. '124.0.6367.60'), or None if not found.
    """
    # Match "Chrome/…" or "Chromium/…" version format.
    m = re.search(r'(?:Chrome|Chromium)/([0-9.]+)', ua)
    if m:
        return m.group(1)
    return None


def generate_sec_ch_ua(ua):
    """
    Generate a `Sec-CH-UA` client hint string from a Chromium-based user-agent.

    @param ua (str) Full user-agent string.

    @return (str) Formatted `Sec-CH-UA` string like:
      '"Chromium";v="124", "Not-A.Brand";v="99", "Brave";v="124"'

    @raises ValueError if the user-agent is not recognized as Chromium-based.
    """
    brand, brand_version = parse_chromium_ua(ua)
    chromium_version = parse_chromium_version(ua)

    if not brand or not brand_version or not chromium_version:
        raise ValueError("Not a recognized Chromium-based UA string")

    # Construct brand/version list in expected order
    brands = [
        ('Chromium', chromium_version.split('.')[0]),
        ('Not-A.Brand', '99'),
        (brand, brand_version.split('.')[0])
    ]

    # Remove duplicates (e.g., Chrome may show up as both Chromium and Google Chrome)
    unique_brands = []
    seen = set()
    for b, v in brands:
        if b not in seen:
            unique_brands.append((b, v))
            seen.add(b)

    # Randomize order for GREASE behavior
    random.shuffle(unique_brands)

    # Format according to Sec-CH-UA header spec
    sec_ch_ua = ', '.join(f'"{b}";v="{v}"' for b, v in unique_brands)
    return sec_ch_ua


def parse_android_model(ua):
    """
    Extract Android device model name from user-agent string.

    @param ua (str) Full user-agent string.

    @return (str or None) Model name (e.g. 'Pixel 7'), or None if not found.
    """
    # Match common Android model format: 'Android <ver>; <model> Build/...'
    m = re.search(r'Android [^;]+; ([^;]+) Build/', ua)
    if m:
        return m.group(1).strip()
    return None

def generate_sec_ch_ua_model(ua):
    """
    Generate `Sec-CH-UA-Model` value from an Android user-agent string.

    @param ua (str) Full user-agent string.

    @return (str) Model name in quoted format (e.g. '"Pixel 7"'), or '""' if not available.
    """
    model = parse_android_model(ua)
    return f'"{model}"' if model else '""'



def parse_platform_version(ua):
    """
    Extract OS version number from user-agent string.

    @param ua (str) Full user-agent string.

    @return (str or None) Version string (e.g. '13.0', '10.0', '12.6.1'), or None if not matched.
    """
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
    """
    Generate `Sec-CH-UA-Platform-Version` from user-agent string.

    @param ua (str) Full user-agent string.

    @return (str) Version string in quoted format (e.g. '"13.0"'), or '""' if not found.
    """
    version = parse_platform_version(ua)
    return f'"{version}"' if version else '""'

def parse_chromium_full_version(ua):
    """
    Extract full Chromium engine version from user-agent string.

    @param ua (str) Full user-agent string.

    @return (str or None) Full version string (e.g. '114.0.5735.198'), or None if not found.
    """
    # Match either Chrome or Chromium version.
    m = re.search(r'(?:Chrome|Chromium)/([0-9.]+)', ua)
    if m:
        return m.group(1)
    return None

def send_ch(ua):
    """
    Determine whether the browser supports and requests client hints.

    @param ua (str) Full user-agent string.

    @return (bool) True if the UA supports `Sec-CH-UA` headers.
    False for Firefox, Safari, or older/non-Chromium browsers.
    """
    ua = ua.lower()

    # Explicitly exclude Firefox and Safari (even on Chromium-based UCBrowser).
    if 'firefox' in ua or 'safari' in ua and 'ucbrowser' in ua and 'chrome' not in ua and 'chromium' not in ua:
        return False

    # Chromium-based browsers and their minimum supported versions for CH.
    chromium_browsers = [
        (r'chrome/(\d+)', 89),
        (r'crios/(\d+)', 89),             # Chrome on iOS
        (r'edg[a]?/(\d+)', 90),           # Microsoft Edge
        (r'opr/(\d+)', 75),               # Opera
        (r'yabrowser/(\d+)', 1),          # Yandex
        (r'miui browser/(\d+)', 1),       # MIUI Browser
        (r'qqbrowser/(\d+)', 10),         # QQBrowser (v10+)
        (r'android.*version/(\d+).*chrome', 84),  # Android Browser
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

    # Not a recognized Chromium-based UA or version too old
    return False

def generate_sec_ch_ua_full_version_list(ua):
    """
    Generate a `Sec-CH-UA-Full-Version-List` client hint string from a Chromium-based user-agent.

    @param ua (str): Full user-agent string.

    @return (str): Formatted `Sec-CH-UA-Full-Version-List` string like:
      '"Chromium";v="114.0.5735.198", "Not-A.Brand";v="99.0.0.0", "Google Chrome";v="114.0.5735.198"'
    """
    brand, brand_version = parse_chromium_ua(ua)
    chromium_version = parse_chromium_full_version(ua)

    if not brand or not brand_version or not chromium_version:
        raise ValueError("Not a recognized Chromium-based UA string")

    brands = [
        ("Chromium", chromium_version),
        ("Not-A.Brand", "99.0.0.0"),
        (brand, chromium_version),
    ]

    # Remove duplicates
    unique = []
    seen = set()
    for b, v in brands:
        if b not in seen:
            unique.append((b, v))
            seen.add(b)

    result = ", ".join(f'"{b}";v="{v}"' for b, v in unique)

    return result



