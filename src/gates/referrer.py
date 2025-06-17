from .base import GateBase

class ReferrerGate(GateBase):
    name = "ReferrerGate"

    async def get_headers(self, referrer=None, **kwargs):
        if referrer:
            print(f"[GATE] Set Referer Header: {referrer}")
            return {"referer": referrer}
        return {}
