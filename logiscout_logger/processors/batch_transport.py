"""
Batch Transport Processor

This processor handles sending batched RequestLogPayload objects.
Used by middleware to send all logs from a request in one batch.
"""

from typing import Any
from ..events import RequestLogPayload
from ..transports.base import Transport


class BatchTransportProcessor:
    """
    Processor that sends batched RequestLogPayload to a transport.
    This is used by middleware, not in the structlog pipeline.
    """

    def __init__(self, transport: Transport):
        self._transport = transport

    def send_payload(self, payload: RequestLogPayload) -> None:
        """
        Send a batched request payload using the configured transport.

        Args:
            payload: RequestLogPayload object containing all logs from a request
        """
        if self._transport and payload:
            self._transport.send_batch(payload)
