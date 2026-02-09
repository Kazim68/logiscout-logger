from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class LogEvent:
    timestamp: datetime
    level: str
    message: str

    logger_name: str

    metadata: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[Dict[str, Any]] = None


@dataclass
class RequestLogPayload:
    """
    Represents a complete request payload containing all logs for a single request.
    This combines request metadata with all logs generated during that request.

    Note: Each log entry contains its own logger_name, so we don't need a global
    service_name or logger_name at the payload level.
    """
    correlationId: str
    startedAt: str  # ISO format timestamp of when request started
    endedAt: str  # ISO format timestamp of when request ended
    durationMS: float  # Request duration in milliseconds
    request: Dict[str, Any]  # Contains method, path, statusCode
    logs: List[Dict[str, Any]] = field(default_factory=list)  # Array of log entries

    def to_dict(self) -> Dict[str, Any]:
        """Convert the payload to a dictionary for JSON serialization"""
        return {
            "correlationId": self.correlationId,
            "startedAt": self.startedAt,
            "endedAt": self.endedAt,
            "durationMS": self.durationMS,
            "request": self.request,
            "logs": self.logs
        }
