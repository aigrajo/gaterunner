from .base import GateBase

class ReferrerGate(GateBase):
    name = "ReferrerGate"

    async def handle(self, page, context, referrer=None, url=None):
        if referrer:
            print(f"[GATE] Set Referer Header: {referrer}")
            await context.set_extra_http_headers({"Referer": referrer})
            return True
        return False
