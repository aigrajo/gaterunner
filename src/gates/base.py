class GateBase:
    name = "base"

    async def handle(self, page, context, geolocation=None):
        """
        Try to bypass the gate on the given page.
        """
        raise NotImplementedError