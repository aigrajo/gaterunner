"""
spoof_manager.py - Unified spoofing orchestrator

Centralizes both HTTP-level (headers, routing) and browser-level (JavaScript patches)
spoofing into a single, coherent system using the gate architecture.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.gates import ALL_GATES
from src.debug import debug_print
from src.utils import TemplateLoader


class SpoofingManager:
    """
    Unified manager for applying both HTTP and JavaScript-level spoofing.
    
    Uses the gate system to orchestrate header spoofing, request routing,
    and browser API patching in a consistent, modular way.
    """
    
    def __init__(self, gates=None):
        """
        Initialize the spoofing manager.
        
        @param gates: List of gate instances to use (defaults to ALL_GATES)
        """
        self.gates = gates or ALL_GATES
        self.template_loader = TemplateLoader()  # Shared template processing
    
    async def apply_spoofing(
        self,
        page,
        context, 
        gate_config: Optional[Dict[str, Any]] = None,
        engine: str = "chromium",
        url: Optional[str] = None,
        resource_request_headers: Optional[Dict] = None
    ):
        """
        Apply both HTTP and browser-level spoofing using enabled gates.
        
        @param page: Playwright page instance
        @param context: Playwright browser context  
        @param gate_config: Dict of gate names -> gate arguments
        @param engine: Browser engine ("chromium", "firefox", "webkit")
        @param url: Target URL for gate processing
        @param resource_request_headers: Dict to store captured headers by URL
        """
        gate_config = gate_config or {}
        
        # 1. Apply HTTP-level spoofing (headers, permissions, routing)
        await self._apply_http_spoofing(
            page, context, gate_config, url, resource_request_headers
        )
        
        # 2. Apply JavaScript patches
        await self._apply_js_patches(context, gate_config, engine)
    
    async def _apply_http_spoofing(
        self,
        page,
        context,
        gate_config: Dict[str, Any],
        url: Optional[str],
        resource_request_headers: Optional[Dict]
    ):
        """Apply HTTP-level spoofing (headers, routing, permissions)."""
        
        # Call handle() on all enabled gates
        for gate in self.gates:
            if self._is_gate_enabled(gate, gate_config):
                args = gate_config.get(gate.name, {}).copy()
                # Special case: provide GPU vendor/renderer to UserAgentGate during context phase
                if gate.name == "UserAgentGate":
                    if "WebGLGate" in gate_config:
                        args.update(gate_config.get("WebGLGate", {}))
                    else:
                        vendor = getattr(self, "_last_template_vars", {}).get("__WEBGL_VENDOR__")
                        renderer = getattr(self, "_last_template_vars", {}).get("__WEBGL_RENDERER__")
                        if vendor and renderer:
                            args.update({"webgl_vendor": vendor, "webgl_renderer": renderer})
                    
                    # Pass timezone from TimezoneGate if available
                    if "TimezoneGate" in gate_config:
                        timezone_args = gate_config.get("TimezoneGate", {})
                        timezone_gate = next((g for g in self.gates if g.name == "TimezoneGate"), None)
                        if timezone_gate:
                            timezone_vars = timezone_gate.get_js_template_vars(**timezone_args)
                            if "timezone_id" in timezone_vars:
                                args["timezone_id"] = timezone_vars["timezone_id"]
                    
                    debug_print(f"[DEBUG] _apply_http_spoofing -> UserAgentGate handle args: vendor={args.get('webgl_vendor')} renderer={args.get('webgl_renderer')} timezone={args.get('timezone_id', 'UTC')}")
                await gate.handle(page, context, **args, url=url)
        
        # Collect headers from all enabled gates
        headers = {}
        for gate in self.gates:
            if self._is_gate_enabled(gate, gate_config):
                args = gate_config.get(gate.name, {})
                gate_headers = await gate.get_headers(**args, url=url)
                headers.update(gate_headers)
        
        # Prepare header injectors
        injectors = [
            gate for gate in self.gates
            if self._is_gate_enabled(gate, gate_config) and hasattr(gate, "inject_headers")
        ]
        
        # Set up route handler for header injection
        async def route_handler(route, request):
            merged_headers = request.headers.copy()
            merged_headers.update(headers)
            
            # Apply dynamic header injection
            for gate in injectors:
                try:
                    gate_headers = gate.inject_headers(request)
                    if gate_headers:
                        merged_headers.update(gate_headers)
                except Exception as e:
                    print(f"[WARN] {gate.name}.inject_headers failed: {e}")
            
            # Store headers if requested
            if resource_request_headers is not None:
                resource_request_headers[request.url] = {
                    "method": request.method,
                    **dict(merged_headers)
                }
            
            await route.continue_(headers=merged_headers)
        
        await context.route("**/*", route_handler)
    
    async def _apply_js_patches(
        self,
        context,
        gate_config: Dict[str, Any], 
        engine: str
    ):
        """Apply JavaScript patches from enabled gates."""
        
        # Collect all template variables from all gates first
        all_template_vars = {}
        
        # Special handling: collect timezone from TimezoneGate first if enabled
        selected_timezone = "UTC"  # default
        for gate in self.gates:
            if self._is_gate_enabled(gate, gate_config) and gate.name == "TimezoneGate":
                args = gate_config.get(gate.name, {})
                timezone_vars = gate.get_js_template_vars(**args)
                if "timezone_id" in timezone_vars:
                    selected_timezone = timezone_vars["timezone_id"]
                    debug_print(f"[DEBUG] Using timezone from TimezoneGate: {selected_timezone}")
                break
        
        for gate in self.gates:
            if self._is_gate_enabled(gate, gate_config):
                args = gate_config.get(gate.name, {})
                # Pass timezone to gates that need it
                if gate.name in ["UserAgentGate", "LanguageGate"]:
                    args = args.copy()
                    args["timezone_id"] = selected_timezone
                gate_template_vars = gate.get_js_template_vars(**args)
                all_template_vars.update(gate_template_vars)
        
        # 🔧 Persist template vars for later (e.g., worker GPU sync)
        self._last_template_vars = all_template_vars.copy()
        
        # Then apply patches with the merged template variables
        for gate in self.gates:
            if self._is_gate_enabled(gate, gate_config):
                args = gate_config.get(gate.name, {})
                
                # Pass browser_engine from top-level config to each gate
                if "browser_engine" in gate_config:
                    args = args.copy()  # Don't modify the original
                    args["browser_engine"] = gate_config["browser_engine"]
                
                # Get JS patches for this gate
                patch_names = gate.get_js_patches(engine=engine, **args)
                
                # Debug: show if patches were skipped due to browser engine
                if "browser_engine" in args and args["browser_engine"] in ["patchright", "camoufox"]:
                    debug_print(f"[DEBUG] Skipped JS patches for {gate.name} (browser_engine={args['browser_engine']})")
                elif not patch_names:
                    debug_print(f"[DEBUG] No JS patches for {gate.name}")
                else:
                    debug_print(f"[DEBUG] Got {len(patch_names)} JS patches for {gate.name}: {patch_names}")
                
                # Apply each patch with merged template variables
                for patch_name in patch_names:
                    try:
                        js_code = self.template_loader.load_and_render_template(patch_name, all_template_vars)
                        await context.add_init_script(js_code)
                        debug_print(f"[DEBUG] Applied JS patch: {patch_name} (via {gate.name})")
                    except Exception as e:
                        print(f"[WARN] Failed to apply JS patch {patch_name}: {e}")
    
    # Template processing moved to shared TemplateLoader utility
    
    async def setup_page_handlers(
        self,
        page,
        context,
        gate_config: Optional[Dict[str, Any]] = None
    ):
        """
        Set up page-specific handlers (like worker event listeners) after page creation.
        
        @param page: Playwright page instance
        @param context: Playwright browser context
        @param gate_config: Dict of gate names -> gate arguments
        """
        gate_config = gate_config or {}
        
        # Call setup_page_handlers on all enabled gates that have it
        for gate in self.gates:
            if self._is_gate_enabled(gate, gate_config) and hasattr(gate, "setup_page_handlers"):
                args = gate_config.get(gate.name, {}).copy()
                
                # Pass browser_engine from top-level config to each gate
                if "browser_engine" in gate_config:
                    args["browser_engine"] = gate_config["browser_engine"]
                
                # Special case: UserAgentGate needs WebGL vendor/renderer for worker spoof
                if gate.name == "UserAgentGate":
                    if "WebGLGate" in gate_config:
                        args.update(gate_config.get("WebGLGate", {}))
                    else:
                        # Fallback: pull from last template vars if available
                        vendor = getattr(self, "_last_template_vars", {}).get("__WEBGL_VENDOR__")
                        renderer = getattr(self, "_last_template_vars", {}).get("__WEBGL_RENDERER__")
                        if vendor and renderer:
                            args.update({"webgl_vendor": vendor, "webgl_renderer": renderer})
                    
                    # Pass timezone from TimezoneGate if available
                    if "TimezoneGate" in gate_config:
                        timezone_args = gate_config.get("TimezoneGate", {})
                        timezone_gate = next((g for g in self.gates if g.name == "TimezoneGate"), None)
                        if timezone_gate:
                            timezone_vars = timezone_gate.get_js_template_vars(**timezone_args)
                            if "timezone_id" in timezone_vars:
                                args["timezone_id"] = timezone_vars["timezone_id"]
                    
                    debug_print(f"[DEBUG] apply_spoofing -> UserAgentGate args: vendor={args.get('webgl_vendor')} renderer={args.get('webgl_renderer')} timezone={args.get('timezone_id', 'UTC')}")
                try:
                    await gate.setup_page_handlers(page, context, **args)
                    debug_print(f"[DEBUG] Set up page handlers for {gate.name}")
                except Exception as e:
                    print(f"[WARN] Failed to setup page handlers for {gate.name}: {e}")

    def _is_gate_enabled(self, gate, gate_config: Dict[str, Any]) -> bool:
        """Check if a gate is enabled in the configuration."""
        # If gate has explicit config, it's enabled
        if gate.name in gate_config:
            return True
        
        # Default behavior: enabled unless explicitly disabled
        gates_enabled = gate_config.get("gates_enabled", {})
        return gates_enabled.get(gate.name, True) 