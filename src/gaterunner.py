# gaterunner.py

from src.clienthints import send_ch
from .gates import ALL_GATES

async def run_gates(page, context, gates_enabled=None, gate_args=None, url=None, resource_request_headers=None):
    """
    Execute all enabled gate bypass techniques and configure spoofed request headers.

    @param page (Playwright Page) The page instance where navigation occurs.
    @param context (Playwright BrowserContext) Browser context to set up routing and header overrides.
    @param gates_enabled (dict or None) Dict of gate names -> bool to enable/disable each gate.
    @param gate_args (dict or None) Dict of gate names -> dict of arguments to pass to their handle() or get_headers().
    @param url (str or None) Target URL used by gates during processing.
    @param resource_request_headers (dict or None) Dict to store captured request headers by URL.

    @return (None) Sets up internal header spoofing and routing.
    """
    gates_enabled = gates_enabled or {}
    gate_args = gate_args or {}

    # Call handle() on all enabled gates with their configured args.
    for gate in ALL_GATES:
        if gates_enabled.get(gate.name, True):
            args = gate_args.get(gate.name, {})
            await gate.handle(page, context, **args, url=url)

    # Collect headers returned from get_headers() on each gate.
    headers = {}
    for gate in ALL_GATES:
        if gates_enabled.get(gate.name, True):
            args = gate_args.get(gate.name, {})
            gate_headers = await gate.get_headers(**args, url=url)
            headers.update(gate_headers)

    # Prepare header injectors from gates that define inject_headers()
    injectors = [
        gate for gate in ALL_GATES
        if gates_enabled.get(gate.name, True) and hasattr(gate, "inject_headers")
    ]

    # Define route handler to intercept requests and inject spoofed headers.
    async def route_handler(route, request):
        merged_headers = request.headers.copy()
        merged_headers.update(headers)

        for gate in injectors:
            try:
                gate_headers = gate.inject_headers(request)
                if gate_headers:
                    merged_headers.update(gate_headers)
            except Exception as e:
                print(f"[WARN] {gate.name}.inject_headers failed: {e}")

        if resource_request_headers is not None:
            resource_request_headers[request.url] = {
                "method": request.method,
            }
            resource_request_headers[request.url].update(dict(merged_headers))

        await route.continue_(headers=merged_headers)

    await context.route("**/*", route_handler)
