# useragent.py
import asyncio
import json
import random
from typing import Dict

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
from ..debug import debug_print

# ───────────────────────── types ──────────────────────────

UserAgentEntry = dict[str, str]

# ───────────────────────── functions ──────────────────────────

def choose_ua(key: str) -> str:
    """Randomly choose a User-Agent string from a JSON file category.

    @param key (str): Category key (e.g. 'desktop', 'mobile') from user-agents.json.

    @return (str): A random User-Agent string.
    @raise ValueError: If the category key is missing or empty.
    """
    with open('src/data/user-agents.json', newline='') as jsonfile:
        ua_data: dict[str, list[UserAgentEntry]] = json.load(jsonfile)

    if key not in ua_data or not ua_data[key]:
        raise ValueError(f"No agents found in category: {key}")

    ua_obj = random.choice(ua_data[key])
    return ua_obj["userAgent"]

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

    def build_spoof_js(self, navigator_ref="navigator", window_ref="window", **kwargs):
        """
        Build spoofing JavaScript using external template file.
        """
        import json, textwrap, pathlib
        # Cache template
        if not hasattr(self, "_worker_template"):
            template_path = pathlib.Path(__file__).resolve().parent.parent / "js" / "worker_spoof_template.js"
            self._worker_template = template_path.read_text(encoding="utf-8")
        template = self._worker_template
        # Prepare values
        spoof_json = json.dumps(kwargs.get("uadata", {})) if "uadata" in kwargs else None  # note
        if spoof_json is None:
            # rebuild uadata as before
            uadata = {
                "brands": [
                    {"brand": kwargs.get("brand", "Chromium"), "version": kwargs.get("brand_v", "114")},
                    {"brand": "Chromium", "version": kwargs.get("brand_v", "114")},
                    {"brand": "Not A;Brand", "version": "99"}
                ],
                "mobile": kwargs.get("mobile", False),
                "platform": "Windows" if kwargs.get("platform", "Win32") == "Win32" else kwargs.get("platform", "Win32"),
                "architecture": kwargs.get("architecture", "x86"),
                "bitness": kwargs.get("bitness", "64"),
                "model": kwargs.get("model", ""),
                "platformVersion": kwargs.get("platformVersion", "10.0.0"),
                "uaFullVersion": kwargs.get("uaFullVersion", "114.0.0.0"),
                "fullVersionList": [
                    {"brand": kwargs.get("brand", "Chromium"), "version": kwargs.get("uaFullVersion", "114.0.0.0")},
                    {"brand": "Chromium", "version": kwargs.get("uaFullVersion", "114.0.0.0")},
                    {"brand": "Not A;Brand", "version": "99.0.0.0"}
                ]
            }
            spoof_json = json.dumps(uadata,separators=(",", ":"))
        languages = kwargs.get("languages", ["en-US","en"])
        languages_json = json.dumps(languages)
        device_memory = kwargs.get("rand_mem",8)
        hc_map={4:4,6:4,8:4,12:8,16:8,24:12,32:16}
        hardware_concurrency=hc_map.get(device_memory,4)
        formatted = template.format(
            nav_ref=navigator_ref,
            win_ref=window_ref,
            spoof_json=spoof_json,
            platform=kwargs.get("platform","Win32"),
            user_agent=kwargs.get("user_agent",""),
            device_memory=device_memory,
            hardware_concurrency=hardware_concurrency,
            language=languages[0],
            languages_json=languages_json,
            webgl_vendor=kwargs.get("webgl_vendor","Intel Inc."),
            webgl_renderer=kwargs.get("webgl_renderer","Intel(R) HD Graphics 530"),
            timezone=kwargs.get("timezone_id","UTC")
        )
        return textwrap.dedent(formatted)

    async def handle(self, page, context, user_agent=None, **kwargs):
        """
        Tracks Accept-CH responses by origin for dynamic client hints injection.
        Worker synchronization is handled in setup_page_handlers() after page creation.
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

        # ── Add worker init script so even early workers get patched ──
        try:
            template_vars = self.get_js_template_vars(user_agent=user_agent, **kwargs)
            # Merge GPU vendor/renderer if available
            if "webgl_vendor" in kwargs:
                template_vars["webgl_vendor"] = kwargs["webgl_vendor"]
            if "webgl_renderer" in kwargs:
                template_vars["webgl_renderer"] = kwargs["webgl_renderer"]

            vendor   = template_vars.get("webgl_vendor", "Intel Inc.")
            renderer = template_vars.get("webgl_renderer", "Intel(R) Iris(R) Plus Graphics 640")
            worker_init_js = self.build_spoof_js("self.navigator", "self", **template_vars)
            await context.add_init_script(worker_init_js)
            debug_print(f"[DEBUG] Worker init script added – vendor: {vendor} | renderer: {renderer}")
            if vendor == "Intel Inc." and renderer.startswith("Intel("):
                debug_print(f"[DEBUG] GPU spoof defaulted to hard-coded Intel values!")
        except Exception as e:
            debug_print(f"[DEBUG] Failed to inject worker init script: {e}")

    async def setup_page_handlers(self, page, context, user_agent=None, **kwargs):
        """
        Set up page-specific handlers like worker synchronization.
        This is called after page creation.
        """
        if not user_agent:
            return
            
        debug_print(f"[DEBUG] Setting up worker synchronization...")
        
        # Get template variables for worker script generation
        template_vars = self.get_js_template_vars(user_agent=user_agent, **kwargs)

        # --- NEW: merge dynamic GPU values from kwargs ---
        if "webgl_vendor" in kwargs:
            template_vars["webgl_vendor"] = kwargs["webgl_vendor"]
        if "webgl_renderer" in kwargs:
            template_vars["webgl_renderer"] = kwargs["webgl_renderer"]

        debug_print(f"[DEBUG] GPU vars → vendor: {template_vars.get('webgl_vendor')} | renderer: {template_vars.get('webgl_renderer')}")
        # --------------------------------------------------

        # Generate worker script using the same approach as the working script
        worker_script = self.build_spoof_js("self.navigator", "self", **template_vars)
        
        # Set up worker event handlers like the working script
        async def handle_worker(worker):
            try:
                debug_print(f"[DEBUG] Injecting spoof script into worker: {worker.url}")
                await worker.evaluate(worker_script)
                debug_print(f"[DEBUG] Successfully spoofed worker: {worker.url}")
            except Exception as e:
                debug_print(f"[DEBUG] Failed to spoof worker {worker.url}: {e}")
        
        async def handle_service_worker(worker):
            try:
                debug_print(f"[DEBUG] Injecting spoof script into service worker: {worker.url}")
                await worker.evaluate(worker_script)
                debug_print(f"[DEBUG] Successfully spoofed service worker: {worker.url}")
            except Exception as e:
                debug_print(f"[DEBUG] Failed to spoof service worker {worker.url}: {e}")
        
        # Register event handlers (same pattern as working script)
        page.on("worker", lambda worker: asyncio.create_task(handle_worker(worker)))
        context.on("serviceworker", lambda worker: asyncio.create_task(handle_service_worker(worker)))
        
        debug_print(f"[DEBUG] Worker event handlers registered successfully")

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
            "mobile": mobile_flag,
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