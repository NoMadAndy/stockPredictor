"""
Utility functions shared across the application.
"""
import os
import sys
from contextlib import contextmanager


@contextmanager
def suppress_yfinance_output():
    """
    Context manager to suppress stdout/stderr from yfinance.
    
    yfinance prints error messages directly to stderr/stdout which clutter the logs.
    This context manager temporarily redirects both streams to the null device
    (os.devnull, which is cross-platform: /dev/null on Unix, NUL on Windows).
    """
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    devnull = None
    try:
        # Open devnull once and use for both stdout and stderr
        devnull = open(os.devnull, 'w')
        sys.stdout = devnull
        sys.stderr = devnull
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        # Clean up file handle safely
        if devnull is not None:
            try:
                devnull.close()
            except Exception:
                pass  # Ignore errors during cleanup
