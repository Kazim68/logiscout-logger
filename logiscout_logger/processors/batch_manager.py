"""
Batch Manager for Request Payloads

This module handles intelligent batching of RequestLogPayload objects.
Batches are sent when:
1. Total logs across all payloads reach 200
2. 30 seconds have elapsed since last batch
"""

import threading
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..events import RequestLogPayload


class BatchManager:
    """
    Manages batching of RequestLogPayload objects with intelligent flushing.
    Thread-safe for concurrent request handling.
    """

    def __init__(self, transport, max_logs: int = 200, max_wait_seconds: float = 30.0):
        """
        Initialize the batch manager.

        Args:
            transport: The transport to use for sending batches
            max_logs: Maximum number of logs before flushing (default: 200)
            max_wait_seconds: Maximum time to wait before flushing (default: 30 seconds)
        """
        self._transport = transport
        self._max_logs = max_logs
        self._max_wait_seconds = max_wait_seconds

        # Batch state
        self._batch: List[Dict[str, Any]] = []  # List of payload dicts
        self._total_logs_count = 0
        self._last_flush_time = time.time()
        self._lock = threading.Lock()

        # Background flushing thread
        self._flush_thread = None
        self._stop_flag = threading.Event()
        self._start_background_flusher()

        # Track incomplete requests (requests that might still be in progress)
        self._incomplete_requests: Dict[str, Dict[str, Any]] = {}

    def add_payload(self, payload: RequestLogPayload) -> None:
        """
        Add a RequestLogPayload to the batch.
        May trigger an immediate flush if log count threshold is reached.

        Args:
            payload: The RequestLogPayload to add
        """
        with self._lock:
            payload_dict = payload.to_dict()
            correlation_id = payload_dict["correlationId"]

            # Check if this is an update to an incomplete request
            if correlation_id in self._incomplete_requests:
                # This is a completion/update of a previously sent incomplete request
                # Send it as a new payload (the backend will merge)
                pass

            # Add to current batch
            self._batch.append(payload_dict)
            self._total_logs_count += len(payload_dict.get("logs", []))

            # Check if we need to flush due to log count
            if self._total_logs_count >= self._max_logs:
                self._flush_batch()

    def _flush_batch(self) -> None:
        """
        Internal method to flush the current batch.
        Must be called with lock held.
        """
        if not self._batch:
            return

        # Determine which payloads are complete and which might be incomplete
        complete_payloads = []
        incomplete_payloads = []
        total_logs_in_batch = 0

        for payload_dict in self._batch:
            logs = payload_dict.get("logs", [])
            correlation_id = payload_dict["correlationId"]

            # If adding this payload would exceed the limit, mark remaining as incomplete
            if total_logs_in_batch + len(logs) <= self._max_logs:
                complete_payloads.append(payload_dict)
                total_logs_in_batch += len(logs)
                # Remove from incomplete tracking if it was there
                self._incomplete_requests.pop(correlation_id, None)
            else:
                # This payload exceeds the limit
                # Check if we can send partial logs from this payload
                remaining_capacity = self._max_logs - total_logs_in_batch

                if remaining_capacity > 0:
                    # Send partial payload with available logs
                    partial_payload = payload_dict.copy()
                    partial_payload["logs"] = logs[:remaining_capacity]
                    complete_payloads.append(partial_payload)

                    # Keep the rest for next batch
                    remaining_payload = payload_dict.copy()
                    remaining_payload["logs"] = logs[remaining_capacity:]
                    incomplete_payloads.append(remaining_payload)

                    # Track as incomplete
                    self._incomplete_requests[correlation_id] = {
                        "last_sent_at": datetime.utcnow().isoformat() + "Z"
                    }
                    total_logs_in_batch = self._max_logs
                else:
                    # No capacity left, keep entire payload for next batch
                    incomplete_payloads.append(payload_dict)

        # Send the batch if we have payloads
        if complete_payloads:
            batch_to_send = {
                "payloads": complete_payloads
                # "batch_metadata": {
                #     "total_requests": len(complete_payloads),
                #     "total_logs": total_logs_in_batch,
                #     "flushed_at": datetime.utcnow().isoformat() + "Z"
                #}
            }

            self._send_batch(batch_to_send)

        # Reset batch state with incomplete payloads
        self._batch = incomplete_payloads
        self._total_logs_count = sum(len(p.get("logs", [])) for p in incomplete_payloads)
        self._last_flush_time = time.time()

    def _send_batch(self, batch: Dict[str, Any]) -> None:
        """
        Send a batch using the transport.
        Must be called with lock held.

        Args:
            batch: The batch dictionary to send
        """
        if self._transport:
            # Use the transport's send_batch_of_batches method
            # This allows any transport (HTTP, Queue, etc.) to handle batch sending
            self._transport.send_batch_of_batches(batch)

    def _background_flush_loop(self) -> None:
        """
        Background thread that periodically flushes the batch based on time.
        """
        while not self._stop_flag.is_set():
            time.sleep(1)  # Check every second

            with self._lock:
                time_since_last_flush = time.time() - self._last_flush_time

                # Flush if we have data and enough time has passed
                if self._batch and time_since_last_flush >= self._max_wait_seconds:
                    self._flush_batch()

    def _start_background_flusher(self) -> None:
        """
        Start the background thread for time-based flushing.
        """
        if self._flush_thread is None or not self._flush_thread.is_alive():
            self._stop_flag.clear()
            self._flush_thread = threading.Thread(
                target=self._background_flush_loop,
                daemon=True,
                name="LogiScout-BatchFlusher"
            )
            self._flush_thread.start()

    def flush(self) -> None:
        """
        Manually flush the current batch.
        Useful for cleanup on application shutdown.
        """
        with self._lock:
            self._flush_batch()

    def shutdown(self) -> None:
        """
        Shutdown the batch manager and flush any remaining data.
        """
        self._stop_flag.set()
        if self._flush_thread:
            self._flush_thread.join(timeout=5.0)

        # Final flush
        self.flush()
