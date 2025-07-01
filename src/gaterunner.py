"""
gaterunner.py

Responsible for enabling gate bypassing techniques. Mainly spoofs http headers
"""

from src.clienthints import send_ch
from .gates import ALL_GATES

async def run_gates(page, context, gates_enabled=None, gate_args=None, url=None, resource_request_headers=None):
    '''
    Enable gate bypassing
    '''
    gates_enabled = gates_enabled or {}
    gate_args = gate_args or {}

    # Run all handle() methods
    for gate in ALL_GATES:
        if gates_enabled.get(gate.name, True):
            args = gate_args.get(gate.name, {})
            await gate.handle(page, context, **args, url=url)

    # Collect headers
    headers = {}
    for gate in ALL_GATES:
        if gates_enabled.get(gate.name, True):
            args = gate_args.get(gate.name, {})
            gate_headers = await gate.get_headers(**args, url=url)
            headers.update(gate_headers)

    # Send headers through one route
    async def route_handler(route, request):
        merged_headers = request.headers.copy()
        merged_headers.update(headers)

        # Remove client hints headers if applicable
        filtered_headers = merged_headers.copy()
        if gates_enabled.get("UserAgentGate", True):
            client_hints = send_ch(str(gate_args.get("UserAgentGate")))
            if not client_hints:
                filtered_headers = {k: v for k, v in merged_headers.items() if not k.lower().startswith("sec-ch-ua")}

        if resource_request_headers is not None:
            resource_request_headers[request.url] = {
                "method": request.method,
            }
            resource_request_headers[request.url].update(dict(filtered_headers))

        await route.continue_(headers=filtered_headers)

    await context.route("**/*", route_handler)