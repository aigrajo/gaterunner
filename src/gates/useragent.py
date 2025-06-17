from .base import GateBase

class UserAgentGate(GateBase):
    name = "UserAgentGate"

    async def handle(self, page, context, user_agent=None, url=None):
        if not user_agent:
            return False

        # Set user agent in browser context
        await context.set_extra_http_headers({"User-Agent": user_agent})

        async def route_handler(route, request):
            headers = request.headers.copy()
            headers["user-agent"] = user_agent
            await route.continue_(headers=headers)

        await context.route("**/*", route_handler)
        print(f"[GATE] User agent spoofed: {user_agent}")
        return True