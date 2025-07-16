import json
from .base import GateBase

# Handles language spoofing for both HTTP headers and browser APIs
class LanguageGate(GateBase):
    name = "LanguageGate"

    async def get_headers(self, accept_language=None, language=None, **kwargs):
        """
        Return Accept-Language HTTP header.
        
        @param accept_language: Full Accept-Language header value
        @param language: Simple language code (fallback)
        """
        lang_header = accept_language or language
        if lang_header:
            print(f"[GATE] Set Language Header: {lang_header}")
            return {"accept-language": lang_header}
        return {}

    def get_js_patches(self, engine="chromium", accept_language=None, language=None, **kwargs):
        """
        Return JavaScript patches for language spoofing.
        
        Firefox and WebKit need browser-level language spoofing.
        """
        if engine in ["firefox", "webkit"] and (accept_language or language):
            return ["fwk_stealth.js"]
        return []

    def get_js_template_vars(self, accept_language=None, language=None, timezone_id="UTC", user_agent=None, **kwargs):
        """
        Return template variables for language-related JavaScript patches.
        
        Used primarily by fwk_stealth.js for Firefox/WebKit.
        """
        lang_header = accept_language or language
        if not lang_header:
            return {}
        
        # Parse languages from Accept-Language header
        primary = lang_header.split(",", 1)[0].strip()
        languages = [primary]
        if "-" in primary:
            languages.append(primary.split("-", 1)[0])
        
        return {
            "__LANG_JS__": json.dumps(languages),
            "__TZ__": timezone_id,
            "__USER_AGENT__": user_agent or "",
        }
