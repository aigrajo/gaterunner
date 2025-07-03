# useragent.py
import asyncio
from src.clienthints import (
    send_ch,
    generate_sec_ch_ua,
    generate_sec_ch_ua_model,
    parse_platform_version,
    parse_chromium_full_version,
    extract_high_entropy_hints
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
        Tracks Accept-CH responses and dynamically injects requested CH headers.
        """
        if not user_agent or not send_ch(user_agent):
            return

        # Cache Accept-CH headers per origin
        accept_ch_by_origin = self._accept_ch_by_origin

        context.on("response", lambda resp: asyncio.create_task(self._track_accept_ch(resp, accept_ch_by_origin)))

        async def route_handler(route, request):
            origin = "/".join(request.url.split("/", 3)[:3])
            requested = accept_ch_by_origin.get(origin, [])

            extra_ch = {}
            if requested:
                entropy = extract_high_entropy_hints(user_agent)

                if "sec-ch-ua-model" in requested:
                    extra_ch["sec-ch-ua-model"] = f'"{entropy.get("model", "")}"'

                if "sec-ch-ua-platform-version" in requested:
                    v = entropy.get("platformVersion") or parse_platform_version(user_agent)
                    extra_ch["sec-ch-ua-platform-version"] = f'"{v}"' if v else '""'

                if "sec-ch-ua-full-version" in requested:
                    full_ver = parse_chromium_full_version(user_agent)
                    extra_ch["sec-ch-ua-full-version"] = f'"{full_ver}"' if full_ver else '""'

                if "sec-ch-ua-arch" in requested:
                    extra_ch["sec-ch-ua-arch"] = f'"{entropy.get("architecture", "")}"'

                if "sec-ch-ua-bitness" in requested:
                    extra_ch["sec-ch-ua-bitness"] = f'"{entropy.get("bitness", "")}"'

                if "sec-ch-ua-wow64" in requested:
                    wow64 = entropy.get("wow64", False)
                    extra_ch["sec-ch-ua-wow64"] = "?1" if wow64 else "?0"

                if "sec-ch-ua-full-version-list" in requested:
                    # Fallback to sec-ch-ua if you don't store full version list
                    extra_ch["sec-ch-ua-full-version-list"] = generate_sec_ch_ua(user_agent)

            merged = request.headers.copy()
            merged.update(extra_ch)
            await route.continue_(headers=merged)

        await context.route("**/*", route_handler)

    async def _track_accept_ch(self, resp, store):
        origin = "/".join(resp.url.split("/", 3)[:3])
        accept_ch = resp.headers.get("accept-ch")
        if accept_ch:
            store[origin] = [h.strip().lower() for h in accept_ch.split(",")]
            print(f"[UserAgentGate] Accept-CH for {origin}: {store[origin]}")
