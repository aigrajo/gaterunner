"""
utils.py - Shared utilities for template processing and file path handling

Consolidates commonly used functionality across multiple modules.
"""

import hashlib
import os
from pathlib import Path
from typing import Dict, Any


# ───────────────────────── Template Processing ──────────────────────────

class TemplateLoader:
    """
    Shared template loading and rendering utility.
    
    Consolidates template processing logic that was duplicated between
    SpoofingManager and UserAgentGate.
    """
    
    def __init__(self, js_dir: Path = None):
        """
        Initialize template loader.
        
        @param js_dir: Directory containing JavaScript template files
        """
        self.js_dir = js_dir or Path(__file__).resolve().parent / "js"
        self.js_templates_cache = {}  # Cached JS templates
    
    def load_and_render_template(self, patch_name: str, template_vars: Dict[str, Any]) -> str:
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
        
        return rendered


# ───────────────────────── File Path Utilities ──────────────────────────

# Leave a little slack for parent-dir prefix when computing max length.
_MAX_FILENAME_LEN = 240  # 255 is the usual hard limit on most POSIX filesystems.

def safe_filename(stem: str, ext: str, salt: str) -> str:
    """Return *stem* + '_' + 8-hex-md5 + *ext*, trimming *stem* if needed.

    @param stem (str): Base filename without extension.
    @param ext (str): File extension, including leading dot.
    @param salt (str): Salt value used to generate deterministic MD5 suffix.

    @return (str): Sanitized filename safe for saving to disk.
    """

    salt_hash = hashlib.md5(salt.encode()).hexdigest()[:8]
    # room for underscore between stem and salt
    budget = _MAX_FILENAME_LEN - len(ext) - len(salt_hash) - 1
    if budget < 8:
        # pathological: give up on the stem entirely.
        return f"{salt_hash}{ext}"
    if len(stem) > budget:
        stem = stem[:budget]
    return f"{stem}_{salt_hash}{ext}"


def make_slug(netloc: str, path: str, max_len: int = 80) -> str:
    """
    Create a filesystem-safe slug from netloc and path components.
    
    @param netloc: Network location (domain) part of URL
    @param path: Path part of URL  
    @param max_len: Maximum length for the slug
    @return: Sanitized slug with hash suffix for uniqueness
    """
    raw = f"{netloc}_{path}".rstrip("_")
    tail = hashlib.md5(raw.encode()).hexdigest()[:8]   # 8-char hash keeps slugs unique
    if len(raw) > max_len:
        raw = raw[:max_len]
    return f"{raw}_{tail}"


def dedup_path(path: Path) -> Path:
    """
    Avoid clobbering when a name repeats in one crawl session.
    
    @param path: Path object to make unique
    @return: Path object that doesn't conflict with existing files
    """
    counter = 1
    stem, ext = path.stem, path.suffix
    while path.exists():
        path = path.with_name(f"{stem}_{counter}{ext}")
        counter += 1
    return path


def create_output_dir_slug(url: str, base_dir: str) -> str:
    """
    Create output directory path with URL-based slug.
    
    @param url: Full URL to create slug from
    @param base_dir: Base directory path
    @return: Full output directory path with slug
    """
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    netloc = parsed.netloc.replace(":", "_")
    path = parsed.path.strip("/").replace("/", "_") or "root"
    slug = make_slug(netloc, path)
    return os.path.join(os.path.dirname(base_dir), f"saved_{slug}")


# ───────────────────────── Gate Configuration Utilities ──────────────────────────

def resolve_dynamic_gate_args(gate_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert selection criteria to randomized values for this browser context.
    
    Handles per-context randomization for gates that support dynamic values:
    - GeolocationGate: country_code -> random coordinates within country
    - UserAgentGate: ua_selector -> random UA matching criteria
    
    @param gate_args: Gate configuration with selection criteria
    @return: Gate configuration with resolved random values
    """
    
    resolved = gate_args.copy()
    
    # Handle geolocation randomization
    if ("GeolocationGate" in resolved and 
        "country_code" in resolved["GeolocationGate"]):
        from src.gates.geolocation import jitter_country_location
        cc = resolved["GeolocationGate"]["country_code"]
        resolved["GeolocationGate"] = {
            **resolved["GeolocationGate"],
            "geolocation": jitter_country_location(cc)
        }
    
    # Handle user agent randomization  
    if ("UserAgentGate" in resolved and 
        "ua_selector" in resolved["UserAgentGate"]):
        from src.gates.useragent import choose_ua
        selector = resolved["UserAgentGate"]["ua_selector"]
        resolved["UserAgentGate"] = {
            **resolved["UserAgentGate"],
            "user_agent": choose_ua(selector)
        }
    
    return resolved 