"""
debug.py - Debug output utilities

Provides a centralized way to control debug output across the application.
"""

# Global debug flag - set by main.py or other entry points
_VERBOSE = False


def set_verbose(enabled: bool):
    """Set the global verbose flag.
    
    @param enabled: Whether to enable verbose debug output
    """
    global _VERBOSE
    _VERBOSE = enabled


def debug_print(*args, **kwargs):
    """Print debug message only if verbose mode is enabled.
    
    @param args: Arguments to pass to print()
    @param kwargs: Keyword arguments to pass to print()
    """
    if _VERBOSE:
        print(*args, **kwargs)


def is_verbose() -> bool:
    """Check if verbose mode is enabled.
    
    @return: True if verbose mode is enabled
    """
    return _VERBOSE 