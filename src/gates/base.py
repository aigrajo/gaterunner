# Base class for gates, use to implement new gate bypassing
class GateBase:
    name = "base"

    async def handle(self, page, context, **kwargs):
        """
        For non-header actions
        """
        pass

    async def get_headers(self, **kwargs):
        """
        Return headers to spoof
        """
        return {}