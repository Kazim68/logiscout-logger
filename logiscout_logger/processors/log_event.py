from datetime import datetime
from typing import Any, Dict

from ..events import LogEvent
from ..levels import LogLevel


# Keys that structlog already uses internally
_RESERVED_KEYS = {
    "event",
    "level",
    "timestamp",
    "logger",
    "exception",
    "stack",
}


def build_log_event(logger, method_name: str, event_dict: Dict[str, Any]):
    """
    Structlog processor that converts event_dict into LogEvent.
    This processor should be used ONLY for remote logging.
    """

    # --- Core fields ---
    message = event_dict.get("event")
    level = event_dict.get("level", method_name)

    # Normalize level
    try:
        level = LogLevel(level).value
    except ValueError:
        level = LogLevel.INFO.value

    # Timestamp
    ts = event_dict.get("timestamp")
    if isinstance(ts, str):
        timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    else:
        timestamp = datetime.utcnow()

    # Logger name
    logger_name = event_dict.get("logger")

    # Exception (already formatted by structlog)
    exception = event_dict.get("exception")

    # --- Metadata ---
    metadata = {
        k: v
        for k, v in event_dict.items()
        if k not in _RESERVED_KEYS
    }

    log_event = LogEvent(
        timestamp=timestamp,
        level=level,
        message=message,
        logger_name=logger_name,
        metadata=metadata,
        exception={"traceback": exception} if exception else None,
    )

    # Attach for transport processor
    event_dict["_log_event"] = log_event

    return event_dict
