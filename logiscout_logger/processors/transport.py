from typing import Any, Dict
from ..transports.base import Transport


class TransportProcessor:
    """
    Structlog processor that sends LogEvent to a transport.
    """

    def __init__(self, transport: Transport):
        self._transport = transport

    def __call__(self, logger, method_name: str, event_dict: Dict[str, Any]):
        """
        Makes the processor callable
        """
        log_event = event_dict.get("_log_event")

        if log_event:
            self._transport.send(log_event)

        # IMPORTANT: return event_dict so console rendering continues
        return event_dict
