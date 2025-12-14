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
    devnull_stdout = None
    devnull_stderr = None
    try:
        devnull_stdout = open(os.devnull, 'w')
        devnull_stderr = open(os.devnull, 'w')
        sys.stdout = devnull_stdout
        sys.stderr = devnull_stderr
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        # Clean up file handles safely
        if devnull_stdout is not None:
            try:
                devnull_stdout.close()
            except Exception:
                pass  # Ignore errors during cleanup
        if devnull_stderr is not None:
            try:
                devnull_stderr.close()
            except Exception:
                pass  # Ignore errors during cleanup
