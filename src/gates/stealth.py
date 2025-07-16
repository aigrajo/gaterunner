"""
stealth.py - General browser stealth patches gate

Handles generic browser fingerprinting protection patches that
are applied across all browser engines and user agents.
"""

from .base import GateBase


class StealthGate(GateBase):
    name = "StealthGate"
    
    # General stealth patches (browser-agnostic)
    GENERAL_PATCHES = [
        "font_mask.js",
        "webrtc_leak_block.js", 
        "performance_timing.js",
        "incognito.js",
        "dpr_css_patch.js",
        "gamepad_midi_hid.js",
        "sensor_api_stub.js",
    ]
    
    async def handle(self, page, context, **kwargs):
        """
        Stealth gate doesn't need special page/context handling.
        """
        pass
    
    async def get_headers(self, **kwargs):
        """
        Stealth gate doesn't add HTTP headers.
        """
        return {}
    
    def get_js_patches(self, engine="chromium", enabled=True, use_isolation=False, **kwargs):
        """
        Return JavaScript patches for general stealth protection.
        
        @param engine: Browser engine ("chromium", "firefox", "webkit")
        @param enabled: Whether stealth patches should be applied
        @param use_isolation: Whether to use Patchright-style isolated execution (experimental)
        @return: List of JS patch file names
        """
        if not enabled:
            return []
        
        patches = self.GENERAL_PATCHES.copy()
        
        # Add isolated execution for Patchright-style CDP detection avoidance
        if use_isolation:
            patches.insert(1, "isolated_execution.js")  # After native_function_cloner.js
        
        return patches
    
    def get_js_template_vars(self, **kwargs):
        """
        Stealth patches generally don't need template variables.
        """
        return {} 