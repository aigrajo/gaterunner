"""
debug.py - Debug output utilities

Provides a centralized way to control debug output across the application.
This module helps reduce log noise in production while enabling detailed
debugging when needed.

Usage:
    # Set verbose mode globally
    set_verbose(True)
    
    # Use in modules
    debug_print("[DEBUG] This only shows in verbose mode")
    
    # Check verbose state
    if is_verbose():
        # Expensive debug operations
        pass
"""

import sys
from typing import Any

# Global debug flag - set by main.py or other entry points
_VERBOSE = False


def set_verbose(enabled: bool) -> None:
    """Set the global verbose flag.
    
    @param enabled: Whether to enable verbose debug output
    """
    global _VERBOSE
    _VERBOSE = enabled


def debug_print(*args: Any, **kwargs: Any) -> None:
    """Print debug message only if verbose mode is enabled.
    
    @param args: Arguments to pass to print()
    @param kwargs: Keyword arguments to pass to print()
    """
    if _VERBOSE:
        print(*args, **kwargs)


def debug_print_error(*args: Any, **kwargs: Any) -> None:
    """Print debug error message to stderr only if verbose mode is enabled.
    
    @param args: Arguments to pass to print()
    @param kwargs: Keyword arguments to pass to print()
    """
    if _VERBOSE:
        print(*args, file=sys.stderr, **kwargs)


def is_verbose() -> bool:
    """Check if verbose mode is enabled.
    
    @return: True if verbose mode is enabled
    """
    return _VERBOSE


def with_debug_context(context: str):
    """Decorator to add context to debug messages.
    
    @param context: Context string to prepend to debug messages
    @return: Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if _VERBOSE:
                debug_print(f"[{context}] Entering {func.__name__}")
            try:
                result = func(*args, **kwargs)
                if _VERBOSE:
                    debug_print(f"[{context}] Exiting {func.__name__}")
                return result
            except Exception as e:
                if _VERBOSE:
                    debug_print_error(f"[{context}] Error in {func.__name__}: {e}")
                raise
        return wrapper
    return decorator 