from .base import GateBase
from src.clienthints import send_ch, generate_sec_ch_ua, generate_sec_ch_ua_model, generate_sec_ch_ua_platform_version, \
    generate_sec_ch_ua_full_version


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
                headers['sec-ch-ua-platform-version'] = generate_sec_ch_ua_platform_version(user_agent)
                headers['sec-ch-ua-full-version'] = generate_sec_ch_ua_full_version(user_agent)

        return headers