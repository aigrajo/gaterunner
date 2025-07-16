"""
webgl.py - WebGL renderer and vendor spoofing gate

Handles spoofing of WebGL renderer and vendor information to match
the expected hardware for the given user agent.
"""

import random
from .base import GateBase


class WebGLGate(GateBase):
    name = "WebGLGate"
    
    # WebGL renderer/vendor pairs by operating system
    WEBGL_BY_OS = {
        "windows": [
            ("NVIDIA Corporation", "NVIDIA GeForce RTX 3060/PCIe/SSE2"),
            ("NVIDIA Corporation", "NVIDIA GeForce GTX 1060/PCIe/SSE2"),
            ("NVIDIA Corporation", "NVIDIA GeForce GTX 1650/PCIe/SSE2"),
            ("Intel", "Intel(R) HD Graphics 530"),
            ("Intel", "Intel(R) Iris(R) Xe Graphics"),
            ("AMD", "AMD Radeon RX 580"),
            ("AMD", "AMD Radeon RX 6700 XT"),
        ],
        "mac": [
            ("Apple Inc.", "Apple M1"),
            ("Apple Inc.", "Apple M2"),
            ("Apple Inc.", "AMD Radeon Pro 560X"),
        ],
        "linux": [
            ("Intel", "Mesa Intel(R) UHD Graphics 620 (KBL GT2)"),
            ("AMD", "AMD Radeon RX 570 Series (POLARIS10, DRM 3.35.0, 5.4.0-42-generic, LLVM 10.0.0)"),
            ("NVIDIA Corporation", "NVIDIA GeForce RTX 3060/PCIe/SSE2"),
        ],
        "android": [
            ("Qualcomm", "Adreno (TM) 640"),
            ("ARM", "Mali-G76 MP16"),
            ("Qualcomm", "Adreno (TM) 730"),
        ],
        "ios": [
            ("Apple Inc.", "Apple A15 GPU"),
            ("Apple Inc.", "Apple A14 GPU"), 
            ("Apple Inc.", "Apple A16 GPU"),
        ]
    }
    
    async def handle(self, page, context, **kwargs):
        """
        WebGL gate doesn't need special page/context handling.
        """
        pass
    
    async def get_headers(self, **kwargs):
        """
        WebGL gate doesn't add HTTP headers.
        """
        return {}
    
    def get_js_patches(self, engine="chromium", webgl_vendor=None, webgl_renderer=None, user_agent=None, **kwargs):
        """
        Return JavaScript patches for WebGL spoofing.
        """
        # Apply WebGL patch if we have explicit vendor/renderer OR user agent to auto-detect from
        if (webgl_vendor and webgl_renderer) or user_agent:
            return ["webgl_patch.js"]
        return []
    
    def get_js_template_vars(self, webgl_vendor=None, webgl_renderer=None, user_agent=None, **kwargs):
        """
        Return template variables for WebGL spoofing.
        
        Can either accept explicit vendor/renderer or auto-detect from user agent.
        """
        
        # If explicit vendor/renderer provided, use them
        if webgl_vendor and webgl_renderer:
            vendor = webgl_vendor
            renderer = webgl_renderer
        elif user_agent:
            # Auto-detect from user agent
            vendor, renderer = self._pick_webgl_pair_from_ua(user_agent)
        else:
            # Default fallback
            vendor, renderer = "Intel", "Intel(R) HD Graphics 530"
        
        return {
            "__WEBGL_VENDOR__": vendor,
            "__WEBGL_RENDERER__": renderer,
        }
    
    def _pick_webgl_pair_from_ua(self, user_agent: str) -> tuple[str, str]:
        """
        Pick a realistic WebGL vendor/renderer pair based on user agent OS.
        """
        os_family = self._ua_os_family(user_agent)
        
        if os_family in self.WEBGL_BY_OS:
            pool = self.WEBGL_BY_OS[os_family]
        else:
            # Fallback to Windows pool
            pool = self.WEBGL_BY_OS["windows"]
        
        return random.choice(pool)
    
    def _ua_os_family(self, ua: str) -> str:
        """Detect OS family from user agent string."""
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