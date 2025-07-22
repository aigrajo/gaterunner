"""
network.py - Network connection spoofing gate

Handles spoofing of network connection information (WiFi, cellular, etc.)
that gets exposed through the Network Information API.
"""

from .base import GateBase


class NetworkGate(GateBase):
    name = "NetworkGate"
    
    # Connection profiles mapping to realistic network characteristics
    CONNECTION_PROFILES = {
        "desk_low": ("wifi", "3g", 5, 150, "false"),
        "desk_mid": ("wifi", "4g", 20, 80, "false"), 
        "desk_high": ("ethernet", "4g", 50, 30, "false"),
        "mac_notch": ("wifi", "4g", 25, 60, "false"),
        "chrome_book": ("wifi", "3g", 10, 120, "false"),
        "mobile_high": ("cellular", "5g", 20, 100, "true"),
        
        # Additional common profiles
        "wifi": ("wifi", "4g", 20, 80, "false"),
        "cellular": ("cellular", "4g", 15, 120, "false"),
        "ethernet": ("ethernet", "4g", 50, 30, "false"),
        "slow_wifi": ("wifi", "3g", 8, 150, "false"),
        "fast_wifi": ("wifi", "4g", 40, 50, "false"),
        "5g_mobile": ("cellular", "5g", 25, 100, "true"),
    }
    
    async def handle(self, page, context, connection_profile="wifi", **kwargs):
        """
        Handle network-related setup (permissions, etc.).
        Currently no special handling needed.
        """
        pass
    
    async def get_headers(self, **kwargs):
        """
        Network gate doesn't add HTTP headers.
        """
        return {}
    
    def get_js_patches(self, engine="chromium", connection_profile="wifi", browser_engine=None, **kwargs):
        """
        Return JavaScript patches for network information spoofing.
        """
        # Disable patches for patchright and camoufox (they have built-in stealth)
        if browser_engine in ["patchright", "camoufox"]:
            return []
        
        # Only apply if we have a connection profile configured
        if connection_profile:
            return ["network_info_stub.js"]
        return []
    
    def get_js_template_vars(self, connection_profile="wifi", **kwargs):
        """
        Return template variables for network information spoofing.
        
        @param connection_profile: Network profile name or custom config
        @return: Dict of template variables for network_info_stub.js
        """
        if not connection_profile:
            return {}
        
        # Handle both string profiles and custom config dicts
        if isinstance(connection_profile, str):
            if connection_profile in self.CONNECTION_PROFILES:
                conn_type, eff_type, downlink, rtt, save_data = self.CONNECTION_PROFILES[connection_profile]
            else:
                # Default fallback
                conn_type, eff_type, downlink, rtt, save_data = self.CONNECTION_PROFILES["wifi"]
        elif isinstance(connection_profile, dict):
            # Custom connection config
            conn_type = connection_profile.get("type", "wifi")
            eff_type = connection_profile.get("effectiveType", "4g") 
            downlink = connection_profile.get("downlink", 20)
            rtt = connection_profile.get("rtt", 80)
            save_data = str(connection_profile.get("saveData", False)).lower()
        else:
            # Fallback to default
            conn_type, eff_type, downlink, rtt, save_data = self.CONNECTION_PROFILES["wifi"]
        
        return {
            "__CONN_TYPE__": conn_type,
            "__EFFECTIVE_TYPE__": eff_type,
            "__DOWNLINK__": downlink,
            "__RTT__": rtt,
            "__SAVE_DATA__": save_data,
        } 