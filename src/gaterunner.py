"""
gaterunner.py

Responsible for enabling gate bypassing techniques. Mainly spoofs http headers
"""

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

    # Define route handler to intercept requests and inject spoofed headers.
    async def route_handler(route, request):
        merged_headers = request.headers.copy()
        merged_headers.update(headers)

        # Optionally strip client hints if not needed for the UserAgentGate.
        filtered_headers = merged_headers.copy()
        if gates_enabled.get("UserAgentGate", True):
            # send_ch expects a user-agent string, passed as gate_args["UserAgentGate"]
            client_hints = send_ch(str(gate_args.get("UserAgentGate")))
            if not client_hints:
                filtered_headers = {
                    k: v for k, v in merged_headers.items()
                    if not k.lower().startswith("sec-ch-ua")
                }

        #Collect request metadata by URL.
        if resource_request_headers is not None:
            resource_request_headers[request.url] = {
                "method": request.method,
            }
            resource_request_headers[request.url].update(dict(filtered_headers))

        # Proceed with the request using modified headers.
        await route.continue_(headers=filtered_headers)

    # Apply header modification logic to all outgoing resource requests.
    await context.route("**/*", route_handler)
