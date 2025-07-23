"""
Gaterunner - Automated web saving tool for bypassing malicious TDS gating.

A sophisticated browser fingerprinting evasion tool that captures complete webpages
using Playwright, designed specifically to follow attack chains and capture resources.
"""

__version__ = "1.0.0"

# Main exports for API usage
from .browser import Config, save_page
from .spoof_manager import SpoofingManager
from .resources import ResourceData

__all__ = [
    "Config",
    "save_page", 
    "SpoofingManager",
    "ResourceData",
    "__version__",
] 