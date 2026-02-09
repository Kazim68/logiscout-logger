"""
Request Buffer Management

This module handles buffering of logs per request. Each request (identified by correlation_id)
gets its own buffer that accumulates logs throughout the request lifecycle.
"""

from contextvars import ContextVar
from typing import Dict, Any, Optional
from datetime import datetime
from ..events import RequestLogPayload

# Context variable for request buffers (better for async and thread safety)
_request_buffer: ContextVar[Optional[Dict[str, Any]]] = ContextVar('request_buffer', default=None)


def initialize_buffer(correlation_id: str) -> None:
    """
    Initialize a new buffer for a request.
    Called when a new correlation_id is assigned.

    Args:
        correlation_id: The correlation ID for this request
    """
    buffer_data = {
        "correlation_id": correlation_id,
        "started_at": datetime.utcnow().isoformat() + "Z",  # Record start time
        "request": {},  # Will be populated with method, path, statusCode
        "logs": [],  # Array of log entries
        "started": False,
        "duration_ms": None,
        "ended_at": None
    }
    _request_buffer.set(buffer_data)


def start_buffer() -> None:
    """
    Mark the buffer as started (ready to accept logs).
    Called after the buffer has been initialized.
    """
    buffer = _request_buffer.get()
    if buffer:
        buffer["started"] = True


def add_log_to_buffer(log_entry: Dict[str, Any]) -> None:
    """
    Add a log entry to the current request buffer.

    Args:
        log_entry: The log entry dictionary to add
    """
    buffer = _request_buffer.get()
    if buffer and buffer.get("started"):
        # Create a copy of the log entry
        log_copy = log_entry.copy()

        # Remove fields from metadata that are already at payload level
        # These are captured in request object, so no need in individual log metadata
        metadata = log_copy.get("metadata", {})
        if metadata:
            log_copy["metadata"] = metadata.copy()
            # Remove correlation_id (it's at payload level)
            log_copy["metadata"].pop("correlation_id", None)
            # Remove request context fields (they're in request object)
            log_copy["metadata"].pop("http_method", None)
            log_copy["metadata"].pop("url_path", None)

        buffer["logs"].append(log_copy)


def set_access_log_data(http_method: str, url_path: str, status_code: Optional[int] = None, duration_ms: Optional[float] = None) -> None:
    """
    Set or update request data in the current buffer.

    Args:
        http_method: HTTP method (GET, POST, etc.)
        url_path: Request URL path
        status_code: HTTP response status code (optional, set later)
        duration_ms: Request duration in milliseconds (optional, set later)
    """
    buffer = _request_buffer.get()
    if buffer:
        request_data = {
            "method": http_method,
            "path": url_path
        }

        if status_code is not None:
            request_data["statusCode"] = status_code

        # Merge with existing request data
        buffer["request"].update(request_data)

        # Store duration_ms and ended_at separately at buffer level
        if duration_ms is not None:
            buffer["duration_ms"] = duration_ms
            buffer["ended_at"] = datetime.utcnow().isoformat() + "Z"


def get_current_buffer() -> Optional[Dict[str, Any]]:
    """
    Get the current request buffer data.

    Returns:
        The current buffer data or None if no buffer exists
    """
    return _request_buffer.get()


def flush_buffer() -> Optional[RequestLogPayload]:
    """
    Flush the current buffer and return the RequestLogPayload.
    This clears the buffer after retrieving its contents.

    Returns:
        RequestLogPayload if buffer exists and has logs, None otherwise
    """
    buffer_data = _request_buffer.get()

    if not buffer_data:
        return None

    # Only create payload if we have logs
    if not buffer_data.get("logs"):
        # Clear the buffer even if empty
        _request_buffer.set(None)
        return None

    # Create the payload with new format
    payload = RequestLogPayload(
        correlationId=buffer_data["correlation_id"],
        startedAt=buffer_data["started_at"],
        endedAt=buffer_data.get("ended_at", datetime.utcnow().isoformat() + "Z"),
        durationMS=buffer_data.get("duration_ms", 0.0),
        request=buffer_data["request"],
        logs=buffer_data["logs"]
    )

    # Clear the buffer
    _request_buffer.set(None)

    return payload


def clear_buffer() -> None:
    """
    Clear the current buffer without flushing.
    Useful for cleanup in error scenarios.
    """
    _request_buffer.set(None)
