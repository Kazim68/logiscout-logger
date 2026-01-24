import json
from dataclasses import asdict
from datetime import datetime
import requests

from .base import Transport
from ..events import LogEvent


class HTTPTransport(Transport):
    """
    HTTP transport that sends LogEvent to a remote server via POST request.
    """

    def __init__(self, endpoint_url: str):
        self._endpoint_url = endpoint_url

    def send(self, event: LogEvent) -> None:
        """
        Sends the LogEvent to the configured HTTP endpoint.
        """
        payload = asdict(event)

        # Convert datetime to ISO format string for JSON serialization
        if isinstance(payload.get("timestamp"), datetime):
            payload["timestamp"] = payload["timestamp"].isoformat()

        print("sending log payload.....")
        print(payload)
        print("----------------")

        try:
            response = requests.post(
                self._endpoint_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            response.raise_for_status()
        except requests.RequestException as e:
            # Silently fail for now - logging transport shouldn't break the app
            pass
