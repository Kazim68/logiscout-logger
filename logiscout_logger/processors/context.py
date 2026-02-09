"""
Context Processor

This processor is responsible for pushing log events to the request buffer
when running in a request context (with middleware).
"""

from typing import Any, Dict
from ..buffer import add_log_to_buffer


def push_to_request_buffer(logger, method_name: str, event_dict: Dict[str, Any]):
    """
    Processor that pushes log events to the request buffer.
    This runs after build_log_event creates the _log_event.

    The log event is added to the buffer if one exists (i.e., we're in a request context).
    If no buffer exists, this is a no-op (logs outside request context).

    Respects the _send flag - if _send is False, the log will not be added to buffer.
    """
    log_event = event_dict.get("_log_event")
    send_flag = event_dict.get("_send", True)  # Default to True if not specified

    # Only add to buffer if send flag is True
    if log_event and send_flag:
        # Convert LogEvent to dict for storage in buffer
        from dataclasses import asdict
        from datetime import datetime

        log_dict = asdict(log_event)

        # Convert datetime to ISO format string for JSON serialization
        if isinstance(log_dict.get("timestamp"), datetime):
            log_dict["timestamp"] = log_dict["timestamp"].isoformat()

        # Add to buffer (no-op if no buffer exists)
        add_log_to_buffer(log_dict)

    # Always return event_dict so console rendering continues
    return event_dict
