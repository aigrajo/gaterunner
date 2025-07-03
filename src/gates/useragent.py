# useragent.py
import asyncio
from src.clienthints import (
    send_ch,
    generate_sec_ch_ua,
)
from .base import GateBase

class UserAgentGate(GateBase):
    name = "UserAgentGate"
    _accept_ch_by_origin = {}

    async def get_headers(self, user_agent=None, **kwargs):
        """
        Return only the default client hints. Dynamic extras are handled during routing.
        """
        headers = {}
        if user_agent:
            headers['user-agent'] = user_agent
            if send_ch(user_agent):
                headers['sec-ch-ua'] = generate_sec_ch_ua(user_agent)
                headers['sec-ch-ua-mobile'] = "?0"  # or dynamically detect
                headers['sec-ch-ua-platform'] = '"Windows"'  # optionally parse from UA

        return headers

    async def handle(self, page, context, user_agent=None, **kwargs):
        """
        Tracks Accept-CH responses by origin for dynamic client hints injection.
        """
        if not user_agent or not send_ch(user_agent):
            return

        self._user_agent = user_agent
        accept_ch_by_origin = self._accept_ch_by_origin

        async def _track(resp):
            origin = "/".join(resp.url.split("/", 3)[:3])
            accept_ch = resp.headers.get("accept-ch")
            if accept_ch:
                accept_ch_by_origin[origin] = [h.strip().lower() for h in accept_ch.split(",")]
                print(f"[GATE] Accept-CH for {origin}: {accept_ch_by_origin[origin]}")

        context.on("response", lambda resp: asyncio.create_task(_track(resp)))

    def inject_headers(self, request):
        """
        Inject extra client hints if Accept-CH was seen for this origin.
        """
        origin = "/".join(request.url.split("/", 3)[:3])
        requested = self._accept_ch_by_origin.get(origin, [])
        if not requested:
            return {}

        from src.clienthints import (
            extract_high_entropy_hints,
            parse_chromium_full_version,
            generate_sec_ch_ua_full_version_list,
        )

        ua = self._user_agent
        entropy = extract_high_entropy_hints(ua)
        headers = {}

        if "sec-ch-ua-model" in requested:
            headers["sec-ch-ua-model"] = f'"{entropy.get("model", "")}"'

        if "sec-ch-ua-platform-version" in requested:
            headers["sec-ch-ua-platform-version"] = f'"{entropy.get("platformVersion", "")}"'

        if "sec-ch-ua-full-version" in requested:
            full_ver = parse_chromium_full_version(ua)
            headers["sec-ch-ua-full-version"] = f'"{full_ver}"' if full_ver else '""'

        if "sec-ch-ua-arch" in requested:
            headers["sec-ch-ua-arch"] = f'"{entropy.get("architecture", "")}"'

        if "sec-ch-ua-bitness" in requested:
            headers["sec-ch-ua-bitness"] = f'"{entropy.get("bitness", "")}"'

        if "sec-ch-ua-wow64" in requested:
            headers["sec-ch-ua-wow64"] = "?1" if entropy.get("wow64", False) else "?0"

        if "sec-ch-ua-full-version-list" in requested:
            headers["sec-ch-ua-full-version-list"] = generate_sec_ch_ua_full_version_list(ua)

        return headers