from .base import GateBase

# Adds referrer link to http requests
class ReferrerGate(GateBase):
    name = "ReferrerGate"

    async def get_headers(self, referrer=None, **kwargs):
        if referrer:
            print(f"[GATE] Set Referer Header: {referrer}")
            return {"referer": referrer}
        return {}
