from .base import GateBase

# Adds referrer link to http requests
class LanguageGate(GateBase):
    name = "LanguageGate"

    async def get_headers(self, language=None, **kwargs):
        if language:
            print(f"[GATE] Set Language Header: {language}")
            return {"accept-language": language}
        return {}
