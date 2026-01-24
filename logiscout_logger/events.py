from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class LogEvent:
    timestamp: datetime
    level: str
    message: str

    logger_name: str

    category: Optional[str] = None  # urana ha isko
    metadata: Dict[str, Any] = field(default_factory=dict)

    file: Optional[str] = None
    line: Optional[int] = None
    function: Optional[str] = None

    exception: Optional[Dict[str, Any]] = None
