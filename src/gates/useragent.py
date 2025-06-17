from .base import GateBase

class UserAgentGate(GateBase):
    name = "UserAgentGate"

    async def get_headers(self, user_agent=None, **kwargs):
        if user_agent:
            print(f"[GATE] User agent spoofed: {user_agent}")
            return {"user-agent": user_agent}
        return {}