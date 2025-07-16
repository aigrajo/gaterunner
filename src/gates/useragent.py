# useragent.py
import asyncio
from src.clienthints import (
    send_ch,
    generate_sec_ch_ua,
    extract_high_entropy_hints,
    parse_chromium_ua,
    parse_chromium_version,
    parse_chromium_full_version,
    generate_sec_ch_ua_full_version_list,
)
from .base import GateBase
import json

class UserAgentGate(GateBase):
    name = "UserAgentGate"
    _accept_ch_by_origin = {}

    async def get_headers(self, user_agent=None, **kwargs):
        """
        Return only the default client hints. Dynamic extras are handled during routing.
        """
        headers = {}
        if user_agent:
            headers['user-agent'] = user_agent
            print(f"[GATE] Spoofed user agent: {user_agent}")
            if send_ch(user_agent):
                headers['sec-ch-ua'] = generate_sec_ch_ua(user_agent)
                headers['sec-ch-ua-mobile'] = "?0"  # or dynamically detect
                headers['sec-ch-ua-platform'] = '"Windows"'  # optionally parse from UA

        return headers

    async def handle(self, page, context, user_agent=None, **kwargs):
        """
        Tracks Accept-CH responses by origin for dynamic client hints injection.
        """
        if not user_agent or not send_ch(user_agent):
            return

        self._user_agent = user_agent
        accept_ch_by_origin = self._accept_ch_by_origin

        async def _track(resp):
            origin = "/".join(resp.url.split("/", 3)[:3])
            accept_ch = resp.headers.get("accept-ch")
            if accept_ch:
                accept_ch_by_origin[origin] = [h.strip().lower() for h in accept_ch.split(",")]
                print(f"[GATE] Accept-CH for {origin}: {accept_ch_by_origin[origin]}")

        context.on("response", lambda resp: asyncio.create_task(_track(resp)))

    def inject_headers(self, request):
        """
        Inject extra client hints if Accept-CH was seen for this origin.
        """
        origin = "/".join(request.url.split("/", 3)[:3])
        requested = self._accept_ch_by_origin.get(origin, [])
        if not requested:
            return {}

        ua = self._user_agent
        entropy = extract_high_entropy_hints(ua)
        headers = {}

        if "sec-ch-ua-model" in requested:
            headers["sec-ch-ua-model"] = f'"{entropy.get("model", "")}"'

        if "sec-ch-ua-platform-version" in requested:
            headers["sec-ch-ua-platform-version"] = f'"{entropy.get("platformVersion", "")}"'

        if "sec-ch-ua-full-version" in requested:
            full_ver = parse_chromium_full_version(ua)
            headers["sec-ch-ua-full-version"] = f'"{full_ver}"' if full_ver else '""'

        if "sec-ch-ua-arch" in requested:
            headers["sec-ch-ua-arch"] = f'"{entropy.get("architecture", "")}"'

        if "sec-ch-ua-bitness" in requested:
            headers["sec-ch-ua-bitness"] = f'"{entropy.get("bitness", "")}"'

        if "sec-ch-ua-wow64" in requested:
            headers["sec-ch-ua-wow64"] = "?1" if entropy.get("wow64", False) else "?0"

        if "sec-ch-ua-full-version-list" in requested:
            headers["sec-ch-ua-full-version-list"] = generate_sec_ch_ua_full_version_list(ua)

        return headers

    def get_js_patches(self, engine="chromium", user_agent=None, **kwargs):
        """
        Return JavaScript patches needed for user-agent spoofing.
        
        Consolidates browser API spoofing that was previously in context.py.
        """
        if not user_agent:
            return []
        
        if engine == "chromium":
            return [
                "spoof_useragent.js",
                "chromium_stealth.js", 
                "extra_stealth.js"
            ]
        else:
            # Firefox/WebKit
            return ["fwk_stealth.js", "extra_stealth.js"]

    def get_js_template_vars(self, user_agent=None, timezone_id="UTC", accept_language=None, rand_mem=8, **kwargs):
        """
        Return template variables for user-agent related JavaScript patches.
        
        Extracts all the client hints and browser fingerprint data.
        """
        if not user_agent:
            return {}
        
        # Extract client hints and browser info
        entropy = extract_high_entropy_hints(user_agent)
        brand, brand_v = parse_chromium_ua(user_agent)
        chromium_v = parse_chromium_version(user_agent)
        mobile_flag = "mobile" in user_agent.lower()
        
        # Map platform names to correct navigator.platform values
        platform_map = {
            "Windows": "Win32",
            "macOS": "MacIntel", 
            "Linux": "Linux x86_64",
            "Android": "Linux armv7l",
            "iOS": "iPhone" if "iPhone" in user_agent else "iPad" if "iPad" in user_agent else "iPhone",
            "Chrome OS": "Linux x86_64",
        }
        detected_platform = entropy.get("platform", "Windows")
        js_platform = platform_map.get(detected_platform, "Win32")
        
        # Parse language information
        if accept_language:
            primary = accept_language.split(",", 1)[0].strip()
            languages = [primary]
            if "-" in primary:
                languages.append(primary.split("-", 1)[0])
        else:
            languages = ["en-US", "en"]
        
        # Base template variables used across multiple patches
        template_vars = {
            # User agent data
            "user_agent": user_agent,
            "USER_AGENT": user_agent,
            
            # Chromium-specific data (for Python format strings in spoof_useragent.js)
            "chromium_v": chromium_v or "",
            "brand": brand,
            "brand_v": brand_v,
            "uaFullVersion": parse_chromium_full_version(user_agent) or chromium_v,
            
            # Client hints entropy data (for Python format strings)
            "architecture": entropy.get("architecture", "x86"),
            "bitness": entropy.get("bitness", "64"),
            "wow64": str(bool(entropy.get("wow64", False))).lower(),
            "model": entropy.get("model", ""),
            "mobile": str(mobile_flag).lower(),
            "platform": js_platform,  # Use mapped JavaScript platform value
            "platformVersion": entropy.get("platformVersion", "15.0"),
            
            # Browser environment
            "TZ": timezone_id,
            "__TZ__": timezone_id,
            
            # Memory info for chromium_stealth.js
            "__RAND_MEM__": rand_mem,
            "RAND_MEM": rand_mem,
            
            # Language data
            "__LANG_JS__": json.dumps(languages),
            "LANG_JS": json.dumps(languages),
            
            # Touch support for mobile
            "touch_js": (
                "Object.defineProperty(window, 'ontouchstart', {value: null});"
                if mobile_flag
                else "if ('ontouchstart' in window) {} else Object.defineProperty(window, 'ontouchstart', {value: null});"
            ),
            "__TOUCH_JS__": (
                "Object.defineProperty(window, 'ontouchstart', {value: null});"
                if mobile_flag
                else "if ('ontouchstart' in window) {} else Object.defineProperty(window, 'ontouchstart', {value: null});"
            ),
            
            # Additional chromium stealth vars (double underscore format)
            "__BRAND__": brand,
            "__BRAND_V__": brand_v,
            "__PLATFORM__": js_platform,  # Use mapped JavaScript platform value
            "__MOBILE__": str(mobile_flag).lower(),
            "__ARCH__": entropy.get("architecture", "x86"),
            "__BITNESS__": entropy.get("bitness", "64"),
            "__MODEL__": entropy.get("model", ""),
            "__PLATFORM_VERSION__": entropy.get("platformVersion", "15.0"),
            "__UA_FULL_VERSION__": parse_chromium_full_version(user_agent) or chromium_v,
            "__WOW64__": str(bool(entropy.get("wow64", False))).lower(),
        }
        
        return template_vars