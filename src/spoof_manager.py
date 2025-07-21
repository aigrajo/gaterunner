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
        self.js_templates_cache = {}  # Cached JS templates
        self.js_dir = Path(__file__).resolve().parent / "js"
    
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
                if gate.name == "UserAgentGate" and "WebGLGate" in gate_config:
                    args.update(gate_config.get("WebGLGate", {}))
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
        
        for gate in self.gates:
            if self._is_gate_enabled(gate, gate_config):
                args = gate_config.get(gate.name, {})
                gate_template_vars = gate.get_js_template_vars(**args)
                all_template_vars.update(gate_template_vars)
        
        # 🔧 Persist template vars for later (e.g., worker GPU sync)
        self._last_template_vars = all_template_vars.copy()
        
        # Then apply patches with the merged template variables
        for gate in self.gates:
            if self._is_gate_enabled(gate, gate_config):
                args = gate_config.get(gate.name, {})
                
                # Get JS patches for this gate
                patch_names = gate.get_js_patches(engine=engine, **args)
                
                # Apply each patch with merged template variables
                for patch_name in patch_names:
                    try:
                        js_code = self._load_and_render_template(patch_name, all_template_vars)
                        await context.add_init_script(js_code)
                        debug_print(f"[DEBUG] Applied JS patch: {patch_name} (via {gate.name})")
                    except Exception as e:
                        print(f"[WARN] Failed to apply JS patch {patch_name}: {e}")
    
    def _load_and_render_template(self, patch_name: str, template_vars: Dict[str, Any]) -> str:
        """
        Load a JS template file and render it with template variables.
        
        @param patch_name: JS file name (e.g., "spoof_useragent.js")
        @param template_vars: Dict of variable names to values for replacement
        @return: Rendered JavaScript code
        """
        
        # Check cache first
        if patch_name in self.js_templates_cache:
            template = self.js_templates_cache[patch_name]
        else:
            # Load from file system
            template_path = self.js_dir / patch_name
            if not template_path.exists():
                raise FileNotFoundError(f"JS template not found: {template_path}")
            
            template = template_path.read_text(encoding="utf-8")
            self.js_templates_cache[patch_name] = template
        
        # Render template with variables using __PLACEHOLDER__ replacement
        rendered = template
        for var_name, var_value in template_vars.items():
            # Handle variables that already have double underscore format vs those that need it added
            if var_name.startswith("__") and var_name.endswith("__"):
                # Variable already in __VAR__ format, use as-is
                placeholder = var_name
            else:
                # Variable needs double underscore format added
                placeholder = f"__{var_name.upper()}__"
            
            rendered = rendered.replace(placeholder, str(var_value))
        
        # Apply Python format() only for known template files that explicitly use Python format syntax
        # Currently only spoof_useragent.js uses {variable} format
        if patch_name == "spoof_useragent.js":
            try:
                rendered = rendered.format(**template_vars)
            except (KeyError, ValueError, IndexError) as e:
                print(f"[WARN] Template format error in {patch_name}: {e}")
                # Don't fail completely, just skip format step
        
        return rendered
    
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
                # Special case: UserAgentGate needs WebGL vendor/renderer for worker spoof
                if gate.name == "UserAgentGate":
                    if "WebGLGate" in gate_config:
                        args.update(gate_config.get("WebGLGate", {}))
                    else:
                        vendor = getattr(self, "_last_template_vars", {}).get("__WEBGL_VENDOR__")
                        renderer = getattr(self, "_last_template_vars", {}).get("__WEBGL_RENDERER__")
                        if vendor and renderer:
                            args.update({"webgl_vendor": vendor, "webgl_renderer": renderer})
                    debug_print(f"[DEBUG] _apply_http_spoofing -> UserAgentGate handle args: vendor={args.get('webgl_vendor')} renderer={args.get('webgl_renderer')}")
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