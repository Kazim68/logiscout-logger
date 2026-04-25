from dataclasses import asdict
from datetime import datetime
import requests

from .base import Transport
from ..events import LogEvent, RequestLogPayload


class HTTPTransport(Transport):
    """
    HTTP transport that sends LogEvent or RequestLogPayload to a remote server via POST request.
    """

    def __init__(self, endpoint_url: str, api_token: str | None = None):
        self._endpoint_url = endpoint_url
        self._api_token = api_token

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"
        return headers

    def send(self, event: LogEvent) -> None:
        """
        Sends the LogEvent to the configured HTTP endpoint.
        (Legacy method - still supported for backward compatibility)
        """
        payload = asdict(event)

        # Convert datetime to ISO format string for JSON serialization
        if isinstance(payload.get("timestamp"), datetime):
            payload["timestamp"] = payload["timestamp"].isoformat()

        # print("sending log payload.....")
        # print(payload)
        # print("----------------")

        try:
            response = requests.post(
                self._endpoint_url,
                json=payload,
                headers=self._headers(),
                timeout=5
            )
            response.raise_for_status()
        except requests.RequestException as e:
            # Silently fail for now - logging transport shouldn't break the app
            pass

    def send_batch(self, payload: RequestLogPayload) -> None:
        """
        Sends a batched RequestLogPayload to the configured HTTP endpoint.
        This is used by middleware to send all logs from a single request.
        """
        payload_dict = payload.to_dict()

        # print("sending batched request payload.....")
        # print(payload_dict)
        # print("----------------")

        try:
            response = requests.post(
                self._endpoint_url,
                json=payload_dict,
                headers=self._headers(),
                timeout=5
            )
            response.raise_for_status()
        except requests.RequestException as e:
            # Silently fail for now - logging transport shouldn't break the app
            pass

    def send_batch_of_batches(self, batch: dict) -> None:
        """
        Sends a batch of RequestLogPayload objects to the configured HTTP endpoint.
        This is used by BatchManager to send multiple requests at once.

        Args:
            batch: Dictionary containing:
                - payloads: List of RequestLogPayload dicts
                - batch_metadata: Metadata about the batch
        """
        # print(f"Sending batch of batches with {batch['batch_metadata']['total_requests']} requests and {batch['batch_metadata']['total_logs']} logs")
        # print(batch)
        # print("----------------")

        try:
            response = requests.post(
                self._endpoint_url,
                json=batch,
                headers=self._headers(),
                timeout=10
            )
            response.raise_for_status()
        except requests.RequestException as e:
            # Silently fail for now - logging transport shouldn't break the app
            print(f"Failed to send batch: {e}")
