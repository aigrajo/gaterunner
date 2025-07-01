from src.clienthints import send_ch, generate_sec_ch_ua, generate_sec_ch_ua_model, parse_chromium_full_version, parse_platform_version
from .base import GateBase


# Spoofs User-Agent string, optionally includes spoofing client hints string
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
                headers['sec-ch-ua-model'] = generate_sec_ch_ua_model(user_agent)
                headers['sec-ch-ua-platform-version'] = parse_platform_version(user_agent)
                headers['sec-ch-ua-full-version'] = parse_chromium_full_version(user_agent)

        return headers