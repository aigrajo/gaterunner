from .base import GateBase
from urllib.parse import urlparse

# Sends browser geolocation data
class GeolocationGate(GateBase):
    name = 'GeolocationGate'

    async def handle(self, page, context, geolocation=None, url=None):
        if geolocation and url:
            parsed_url = urlparse(url)
            origin = f'{parsed_url.scheme}://{parsed_url.netloc}'

            print(f"[GATE] Granted geolocation permissions: {geolocation}")
            await context.grant_permissions(["geolocation"], origin=origin)

            return True
        return False