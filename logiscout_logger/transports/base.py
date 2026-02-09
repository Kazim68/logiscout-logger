from abc import ABC, abstractmethod
from typing import Dict, Any
from ..events import LogEvent, RequestLogPayload


class Transport(ABC):
    """
    Base class for all transports.
    """

    @abstractmethod
    def send(self, event: LogEvent) -> None:
        """Send a single log event"""
        pass

    def send_batch(self, payload: RequestLogPayload) -> None:
        """
        Send a batched RequestLogPayload (single request with multiple logs).
        Default implementation - can be overridden by subclasses.
        """
        pass

    def send_batch_of_batches(self, batch: Dict[str, Any]) -> None:
        """
        Send a batch of RequestLogPayload objects.
        This is used by BatchManager to send multiple requests at once.

        Args:
            batch: Dictionary containing:
                - payloads: List of RequestLogPayload dicts
                - batch_metadata: Metadata about the batch

        Default implementation - should be overridden by subclasses.
        """
        pass
