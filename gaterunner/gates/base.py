# Base class for gates, use to implement new gate bypassing
class GateBase:
    name = "base"

    async def handle(self, page, context, **kwargs):
        """
        For non-header actions (permissions, event listeners, etc.)
        """
        pass

    async def get_headers(self, **kwargs):
        """
        Return headers to spoof
        """
        return {}

    def inject_headers(self, request):
        """
        Dynamic header injection during requests
        """
        return {}

    def get_js_patches(self, engine="chromium", **kwargs):
        """
        Return list of JS patch file names to apply for this gate.
        
        @param engine: Browser engine ("chromium", "firefox", "webkit")
        @param kwargs: Gate-specific arguments
        @return: List of JS file names (without path, e.g., ["spoof_useragent.js"])
        """
        return []

    def get_js_template_vars(self, **kwargs):
        """
        Return variables for JS template replacement.
        
        @param kwargs: Gate-specific arguments  
        @return: Dict of template variable names to values
        """
        return {}