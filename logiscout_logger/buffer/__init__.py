"""
LogiScout Buffer Package

This package handles buffering of log events per request for batched HTTP transport.
"""

from .requestBuffer import (
    initialize_buffer,
    start_buffer,
    add_log_to_buffer,
    flush_buffer,
    get_current_buffer,
    set_access_log_data
)

__all__ = [
    "initialize_buffer",
    "start_buffer",
    "add_log_to_buffer",
    "flush_buffer",
    "get_current_buffer",
    "set_access_log_data"
]
