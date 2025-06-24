"""
context.py – create a Playwright **BrowserContext** with a JavaScript and
network fingerprint that matches the supplied User‑Agent string. This version
adds deeper stealth patches: navigator.userAgentData, navigator.webdriver,
WebRTC/mediaDevices, touch APIs, improved canvas noise and randomised WebGL
vendor/renderer.
"""

from __future__ import annotations

import asyncio
import json
import random
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from playwright.async_api import Browser, BrowserContext, Playwright

# ──────────────────────────────
# Optional: httpagentparser for robust engine detection
# ──────────────────────────────
try:
    import httpagentparser  # type: ignore
    _HAS_HTTPAGENT = True
except ImportError:  # library not installed – fallback to simple rules
    _HAS_HTTPAGENT = False

# ──────────────────────────────
# playwright‑stealth poly‑loader (Chromium only)
# ──────────────────────────────

async def _build_apply_stealth():
    try:  # Stealth ≥ 2 – class API
        Stealth = getattr(import_module("playwright_stealth"), "Stealth")  # type: ignore[attr-defined]
        stealth_inst = Stealth(init_scripts_only=True)

        async def _apply(ctx):
            await stealth_inst.apply_stealth_async(ctx)

        return _apply
    except Exception:
        for fname in ("stealth_async", "stealth"):
            try:
                func = getattr(import_module("playwright_stealth"), fname)  # type: ignore[attr-defined]
                break
            except Exception:
                func = None
        if func is None:
            async def _apply(_: BrowserContext):
                return
            return _apply

        async def _apply(ctx, _f=func):
            await _f(ctx)
        return _apply

_loop = (
    asyncio.get_event_loop()
    if asyncio.get_event_loop_policy().get_event_loop()
    else asyncio.new_event_loop()
)
_apply_stealth = _loop.run_until_complete(_build_apply_stealth())

# ──────────────────────────────
# Local helpers & resources
# ──────────────────────────────

from .clienthints import (  # noqa: E402 – after shim
    extract_high_entropy_hints,
    parse_chromium_full_version,
    parse_chromium_ua,
    parse_chromium_version,
)

_JS_TEMPLATE_PATH = Path(__file__).resolve().parent / "js" / "spoof_useragent.js"
_JS_TEMPLATE = _JS_TEMPLATE_PATH.read_text(encoding="utf-8")

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

_MEM_CHOICES = [4, 6, 8, 12, 16, 24, 32]  # in GiB
_CORE_CHOICES = [4, 6, 8, 12, 16]

# Real WebGL vendor/renderer pairs sourced from real‑world hardware.
_WEBGL_CHOICES: Tuple[Tuple[str, str], ...] = (
    ("Google Inc.", "ANGLE (Intel(R) UHD Graphics 630)"),
    ("Google Inc.", "ANGLE (NVIDIA GeForce RTX 3060 Laptop GPU Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc.", "ANGLE (AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc.", "ANGLE (Apple M1 Pro)"),
)

_WEBGL_BY_OS = {
    "windows": (
        ("NVIDIA Corporation", "NVIDIA GeForce RTX 3060/PCIe/SSE2"),
        ("Intel",              "Intel(R) UHD Graphics 630"),
        ("AMD",                "AMD Radeon RX 6800 XT"),
    ),
    "mac": (
        ("Apple Inc.",         "Apple M1 Pro"),
    ),
    "linux": (
        ("Intel",              "Mesa Intel(R) UHD Graphics 630"),
        ("AMD",                "AMD Radeon RX 6800 XT (RADV NAVI21)"),
    ),
}

# ──────────────────────────────
# NEW – extra browser-surface stealth
# ──────────────────────────────
_EXTRA_STEALTH = r"""
/* extra-stealth (chromium & fwk) */
(() => {
  /* Permissions & Notification */
  if (navigator.permissions?.query) {
    const real = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = p =>
      p && p.name === 'notifications'
        ? Promise.resolve({ state: 'prompt', onchange: null })
        : real(p);
  }
  Object.defineProperty(Notification, 'permission', { get: () => 'default' });
  Notification.requestPermission = async () => 'granted';

  /* Speech-synthesis voices */
  if ('speechSynthesis' in window) {
    const voices = [{
      voiceURI: 'Google US English',
      name:     'Google US English',
      lang:     'en-US',
      localService: true,
      default:  true
    }];
    window.speechSynthesis.getVoices = () => voices;
  }

  /* AudioContext hash jitter */
  const ctxProto = (window.AudioContext || window.webkitAudioContext)?.prototype;
  if (ctxProto && !ctxProto.__patched) {
    const nativeCreate = ctxProto.createAnalyser;
    ctxProto.createAnalyser = function () {
      const analyser = nativeCreate.apply(this, arguments);
      const nativeFFT = analyser.getFloatFrequencyData;
      analyser.getFloatFrequencyData = function (arr) {
        nativeFFT.call(this, arr);
        for (let i = 0; i < arr.length; i += 128) arr[i] += (Math.random() * 1e-4);
      };
      return analyser;
    };
    ctxProto.__patched = true;
  }

  /* mediaDevices.getUserMedia stub */
  if (navigator.mediaDevices && !navigator.mediaDevices.__patched) {
    navigator.mediaDevices.getUserMedia = async () => new MediaStream();
    navigator.mediaDevices.__patched = true;
  }

/* realistic plugins + mimeTypes */
(function () {
  /* use the real empty arrays to keep correct [[Class]] */
  const nativePlugins = navigator.plugins;
  if (nativePlugins.length === 0) {
    const pdfPlugin = Object.freeze({
      description: 'Portable Document Format',
      filename:    'internal-pdf-viewer',
      name:        'PDF Viewer',
      length:      0
    });
    Object.defineProperty(nativePlugins, '0', { value: pdfPlugin, writable: false });
    Object.defineProperty(nativePlugins, 'length', { value: 1, writable: false });
  }

  const nativeMimes = navigator.mimeTypes;
  if (nativeMimes.length === 0) {
    const pdfMime = Object.freeze({
      type:          'application/pdf',
      suffixes:      'pdf',
      description:   '',
      enabledPlugin: nativePlugins[0]
    });
    Object.defineProperty(nativeMimes, '0', { value: pdfMime, writable: false });
    Object.defineProperty(nativeMimes, 'length', { value: 1, writable: false });
  }
})();

    /* privacy flags */
    Object.defineProperty(navigator, 'doNotTrack', { get: () => 'unspecified' });
    
    /* remove Battery Status API so Chrome 116+ behaviour matches */
    (() => {
      const wipe = (obj) => {
        if (!obj || !('getBattery' in obj)) return;
        const ok = delete obj.getBattery;
        if (!ok) {            // if property is non-configurable, shadow it
          try {
            Object.defineProperty(obj, 'getBattery', {
              value: undefined,
              writable: false,
              enumerable: false,
              configurable: false
            });
          } catch (_) {}
        }
      };
      wipe(Navigator.prototype);
      wipe(navigator);
    })();
    if ('getBattery' in navigator) {
      Object.defineProperty(Navigator.prototype, 'getBattery',
        { value: undefined, configurable: false });
      Object.defineProperty(navigator, 'getBattery',
        { value: undefined, configurable: false });
    }
  }
  })();


  /* getClientRects bait tweak */
  const nativeRects = Element.prototype.getClientRects;
  Element.prototype.getClientRects = function () {
    const rects = nativeRects.apply(this, arguments);
    if (rects.length && this.offsetWidth === 0 && this.offsetHeight === 0) {
      const r = rects[0];
      return [new DOMRect(r.x + 0.5, r.y + 0.5, r.width, r.height)];
    }
    return rects;
  };
})();
"""



def _pick_webgl_pair(ua: str) -> Tuple[str, str]:
    low = ua.lower()
    if "mac os" in low or "macos" in low:
        pool = _WEBGL_BY_OS["mac"]
    elif "windows" in low:
        pool = _WEBGL_BY_OS["windows"]
    else:
        pool = _WEBGL_BY_OS["linux"]
    return random.choice(pool)

_SCREEN_CHOICES: Tuple[Tuple[int, int], ...] = (
    (1920, 1080),
    (2560, 1440),
    (1366, 768),
    (1536, 864),
    (2880, 1800),
)


def _engine_from_ua(ua: str) -> str:
    """Best‑effort engine detection from UA string."""
    if _HAS_HTTPAGENT:
        parsed = httpagentparser.detect(ua)  # type: ignore
        browser = (parsed.get("browser") or {})
        name = (browser.get("name") or "").lower()
        if "firefox" in name:
            return "firefox"
        if "safari" in name and "chrome" not in name:
            return "webkit"
        return "chromium"
    # fallback heuristic
    low = ua.lower()
    if "firefox" in low and "seamonkey" not in low:
        return "firefox"
    if "safari" in low and "chrome" not in low and "chromium" not in low:
        return "webkit"
    return "chromium"


def _locale_from_gate(gate_args: Dict[str, Any]) -> Tuple[str, Tuple[str, ...]]:
    raw = gate_args.get("LanguageGate", {}).get("accept_language") if gate_args else None
    if not raw:
        return "en-US", ("en-US", "en")
    primary = raw.split(",", 1)[0].strip()
    return primary, (primary, primary.split("-", 1)[0])


def _timezone_from_gate(gate_args: Dict[str, Any]) -> str:
    return gate_args.get("GeolocationGate", {}).get("timezone_id", "UTC")


# ──────────────────────────────
# JS patch builder for Firefox / WebKit
# ──────────────────────────────

def _fwk_js_patch(languages: Tuple[str, ...], tz: str, mem: int, cores: int) -> str:
    lang_js = json.dumps(list(languages))
    return f"""
/* fwk-stealth (deep) */
Object.defineProperty(navigator, 'languages', {{ get: () => {lang_js} }});
Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions',
  {{ value: () => {{ timeZone: '{tz}' }} }});
Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {mem} }});
Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {cores} }});
Object.defineProperty(navigator, 'vendor', {{ get: () => '' }});
Object.defineProperty(navigator, 'oscpu', {{ get: () => undefined }});
Object.defineProperty(navigator, 'buildID', {{ get: () => undefined }});
Object.defineProperty(navigator, 'productSub', {{ get: () => '20100101' }});
try {{ delete window.navigator.__proto__.mozAddonManager; }} catch(_) {{}}

/* realistic plugin + mimeTypes */
Object.defineProperty(navigator, 'plugins', {{ get: () => [
  {{ name: 'Portable Document Format', filename: 'internal-pdf-viewer',
     description: 'Portable Document Format' }}
] }});
Object.defineProperty(navigator, 'mimeTypes', {{ get: () => [
  {{ type: 'application/pdf', description: '', suffixes: 'pdf',
     enabledPlugin: navigator.plugins[0] }}
] }});

/* WebGL vendor / renderer → Mozilla */
const _get = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(p) {{
  if (p === 37445 || p === 37446) return 'Mozilla';
  return _get.call(this, p);
}};

/* Canvas fingerprint noise – random 3×3 pixel patch */
(() => {{
  const _toURL = HTMLCanvasElement.prototype.toDataURL;
  HTMLCanvasElement.prototype.toDataURL = function() {{
    try {{
      const ctx = this.getContext('2d');
      if (ctx) {{
        const x = Math.floor(Math.random() * this.width);
        const y = Math.floor(Math.random() * this.height);
        ctx.fillRect(x, y, 3, 3);
      }}
    }} catch (_) {{}}
    return _toURL.apply(this, arguments);
  }};
}})();
"""


# ──────────────────────────────
# Public API
# ──────────────────────────────

async def create_context(
    playwright: Playwright,
    gate_args: Optional[Dict[str, Any]] = None,
) -> Tuple[Browser, BrowserContext]:
    """Launch a browser context whose engine and JS surfaces align with the UA."""

    gate_args = gate_args or {}

    ua: str = gate_args.get("UserAgentGate", {}).get("user_agent", _DEFAULT_UA)
    locale, languages = _locale_from_gate(gate_args)
    tz_id = _timezone_from_gate(gate_args)

    engine = _engine_from_ua(ua)

    # Random hardware specs each run
    rand_mem = random.choice(_MEM_CHOICES)
    rand_cores = random.choice(_CORE_CHOICES)

    # Choose screen resolution
    screen_w, screen_h = random.choice(_SCREEN_CHOICES)

    # Choose WebGL vendor/renderer (Chromium only)
    webgl_vendor, webgl_renderer = _pick_webgl_pair(ua)

    # Chromium‑specific high‑entropy hints
    if engine == "chromium":
        entropy = extract_high_entropy_hints(ua)
        brand, brand_v = parse_chromium_ua(ua)
        chromium_v = parse_chromium_version(ua)
        mobile_flag = "mobile" in ua.lower()
    else:
        entropy = {}
        brand = brand_v = chromium_v = ""
        mobile_flag = False

    fp: Dict[str, Any] = {
        "ua": ua,
        "languages": languages,
        "tz": tz_id,
        "mem": rand_mem,
        "cores": rand_cores,
        "screen": (screen_w, screen_h),
        "webgl_vendor": webgl_vendor,
        "webgl_renderer": webgl_renderer,
    }
    if engine == "chromium":
        fp.update(
            brand=brand,
            brand_v=brand_v,
            ua_full_version=parse_chromium_full_version(ua) or chromium_v,
            platform=entropy.get("platform", "Win32"),
            platform_version=entropy.get("platformVersion", "15.0"),
            arch=entropy.get("architecture", "x86"),
            bitness=entropy.get("bitness", "64"),
            wow64=entropy.get("wow64", False),
            mobile=mobile_flag,
        )

    # Launch correct engine
    launcher = getattr(playwright, engine)
    browser: Browser = await launcher.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled"] if engine == "chromium" else [],
    )

    ctx_args: Dict[str, Any] = {
        "user_agent": fp["ua"],
        "locale": locale,
        "timezone_id": fp["tz"],
        "viewport": {"width": screen_w, "height": screen_h},
        "screen": {"width": screen_w, "height": screen_h},
    }
    geo = gate_args.get("GeolocationGate", {}).get("geolocation")
    if geo is not None:
        ctx_args["geolocation"] = geo

    context: BrowserContext = await browser.new_context(**ctx_args)

    # ───────── Chromium path ─────────
    if engine == "chromium":
        await _apply_stealth(context)

        lang_js = json.dumps(list(fp["languages"]))
        touch_js = """if ('ontouchstart' in window) {} else Object.defineProperty(window, 'ontouchstart', {value: null});"""
        if fp.get("mobile"):
            touch_js = "Object.defineProperty(window, 'ontouchstart', {value: null});"

        js_script = _JS_TEMPLATE.format(
            chromium_v=chromium_v or "",
            brand=fp["brand"],
            brand_v=fp["brand_v"],
            architecture=fp.get("arch", "x86"),
            bitness=fp.get("bitness", "64"),
            wow64=str(bool(fp.get("wow64", False))).lower(),
            model=entropy.get("model", ""),
            mobile=str(fp.get("mobile", False)).lower(),
            platform=fp.get("platform", "Win32"),
            platformVersion=fp.get("platform_version", "15.0"),
            uaFullVersion=fp.get("ua_full_version", chromium_v),
        ) + (
            f"""
            Object.defineProperty(navigator, 'languages', {{ get: () => {lang_js} }});
            const _mem = {rand_mem};   // chosen RAM
            Object.defineProperty(navigator, 'deviceMemory', {{ get: () => _mem }});

            const _hc_map = {{4:4,6:4,8:4,12:8,16:8,24:12,32:16}};   // realistic mapping
            Object.defineProperty(navigator, 'hardwareConcurrency', {{
                get: () => _hc_map[_mem] || 4
            }});
            """

        ) + f"\n{touch_js}"

        # Additional deep patches
        js_script += f"""
        /* deep-stealth (chromium) – final */
        (() => {{
          try {{
            /* 1 – remove webdriver */
            delete Navigator.prototype.webdriver;
            delete navigator.webdriver;

            /* 2 – userAgentData */
            const uaData = {{
              brands: [{{ brand: '{fp['brand']}', version: '{fp['brand_v']}' }}],
              platform: '{fp['platform']}',
              mobile: {str(fp['mobile']).lower()},
              getHighEntropyValues: async (hints) => {{
                const src = {{
                  architecture: '{fp['arch']}',
                  bitness: '{fp['bitness']}',
                  model: '{entropy.get('model', '')}',
                  platformVersion: '{fp['platform_version']}',
                  uaFullVersion: '{fp['ua_full_version']}',
                  wow64: {str(fp.get('wow64', False)).lower()}
                }};
                const out = {{}};
                for (const h of hints) if (src[h] !== undefined) out[h] = src[h];
                return out;
              }}
            }};
            Object.defineProperty(navigator, 'userAgentData', {{ get: () => uaData }});

            /* 3 – chrome.runtime stub */
            if (!('chrome' in window)) window.chrome = {{ runtime: {{}} }};
            else if (!('runtime' in window.chrome)) window.chrome.runtime = {{}};
            /* 3b – chrome.loadTimes and chrome.csi stubs */
            if (!('loadTimes' in window.chrome)) {{
              window.chrome.loadTimes = function() {{
                return {{
                  requestTime: Date.now() / 1000,
                  startLoadTime: Date.now() / 1000,
                  commitLoadTime: Date.now() / 1000,
                  finishDocumentLoadTime: Date.now() / 1000,
                  finishLoadTime: Date.now() / 1000,
                  firstPaintTime: Date.now() / 1000,
                  firstPaintAfterLoadTime: 0,
                  navigationType: 'Other',
                  wasFetchedViaSpdy: false,
                  wasNpnNegotiated: false,
                  npnNegotiatedProtocol: '',
                  wasAlternateProtocolAvailable: false,
                  connectionInfo: 'h2'
                }};
              }};
            }}
            if (!('csi' in window.chrome)) {{
              window.chrome.csi = function() {{
                return {{
                  startE: Date.now(),
                  onloadT: Date.now() - performance.timing.navigationStart,
                  pageT: Date.now() - performance.timing.navigationStart,
                  tran: 15
                }};
              }};
            }}
                        
            /* 4 – WebGL spoof */
            const SPOOF_VENDOR   = '{webgl_vendor}';
            const SPOOF_RENDERER = '{webgl_renderer}';
            const CONSTS = {{
              VENDOR:            0x1F00,
              RENDERER:          0x1F01,
              UNMASKED_VENDOR:   0x9245,
              UNMASKED_RENDERER: 0x9246,
            }};

            ['WebGLRenderingContext','WebGL2RenderingContext'].forEach((ctxName) => {{
              const proto = window[ctxName]?.prototype;
              if (!proto) return;

              /* getParameter override */
              const nativeGet = proto.getParameter;
              proto.getParameter = function (p) {{
                switch (p) {{
                  case CONSTS.VENDOR:
                  case CONSTS.UNMASKED_VENDOR:
                    return SPOOF_VENDOR;
                  case CONSTS.RENDERER:
                  case CONSTS.UNMASKED_RENDERER:
                    return SPOOF_RENDERER;
                  default:
                    return nativeGet.call(this, p);
                }}
              }};

              /* WEBGL_debug_renderer_info stub */
              const nativeExt = proto.getSupportedExtensions;
              proto.getSupportedExtensions = function (name) {{
                if (name === 'WEBGL_debug_renderer_info') {{
                  return Object.freeze({{
                    UNMASKED_VENDOR_WEBGL:   CONSTS.UNMASKED_VENDOR,
                    UNMASKED_RENDERER_WEBGL: CONSTS.UNMASKED_RENDERER,
                  }});
                }}
                return nativeExt.call(this, name);
              }};
            }});

            /* OffscreenCanvas shares patched proto */
            if ('OffscreenCanvas' in window) {{
              const realGetCtx = OffscreenCanvas.prototype.getContext;
              OffscreenCanvas.prototype.getContext = function (type, opts) {{
                const ctx = realGetCtx.call(this, type, opts);
                return ctx ?? undefined;
              }};
            }}

            /* 5 – canvas noise (3×3 random pixel) */
            const nativeToURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function () {{
              try {{
                const ctx = this.getContext('2d');
                if (ctx) {{
                  const x = (Math.random() * this.width) | 0;
                  const y = (Math.random() * this.height) | 0;
                  ctx.fillRect(x, y, 3, 3);
                }}
              }} catch (_ignored) {{}}
              return nativeToURL.apply(this, arguments);
            }};

            /* 6 – mediaDevices fallback */
            if (navigator.mediaDevices?.enumerateDevices) {{
              const realEnum = navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
              navigator.mediaDevices.enumerateDevices = async () => {{
                const list = await realEnum();
                if (list.length) return list;
                return [
                  {{ kind: 'audioinput', label: 'Microphone', deviceId: 'default', groupId: 'default' }},
                  {{ kind: 'videoinput', label: 'Camera', deviceId: 'default', groupId: 'default' }}
                ];
              }};
            }}
          }} catch (_err) {{}}
        }})();
        """

        js_script += _EXTRA_STEALTH
        await context.add_init_script(js_script)

    # ───────── Firefox / WebKit path ─────────
    else:
        js_script = _fwk_js_patch(languages, fp["tz"], rand_mem, rand_cores)
        js_script += _EXTRA_STEALTH
        await context.add_init_script(js_script)

    return browser, context




# ──────────────────────────────────────────────────────────
# quick manual CLI test
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    from playwright.async_api import async_playwright

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ua",
        default=_DEFAULT_UA,
        help="User-Agent string to emulate (full header value)",
    )
    args = parser.parse_args()

    async def _demo():
        async with async_playwright() as p:
            browser, ctx = await create_context(
                p, {"UserAgentGate": {"user_agent": args.ua}}
            )
            page = await ctx.new_page()
            await page.goto("https://httpbin.org/headers")
            print(await page.text_content("pre"))
            await browser.close()

    asyncio.run(_demo())
