from .base import GateBase
from .clienthints import send_ch, generate_sec_ch_ua


class UserAgentGate(GateBase):
    name = "UserAgentGate"

    async def get_headers(self, user_agent=None, **kwargs):
        headers = {}
        if user_agent:
            print(f"[GATE] User agent spoofed: {user_agent}")
            headers['user-agent'] = user_agent
            if send_ch(user_agent):
                ch = generate_sec_ch_ua(user_agent)
                print(f'[GATE] Client hints spoofed: {ch}')
                headers['sec-ch-ua'] = ch

        return headers