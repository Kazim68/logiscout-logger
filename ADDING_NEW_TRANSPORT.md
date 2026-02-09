# Adding a New Transport to LogiScout Logger

## Overview

The LogiScout logger is designed with transport abstraction. You can easily add new transports (Queue, Kafka, WebSocket, etc.) by implementing the base `Transport` interface.

**Key Benefit**: Change transport in ONE file (`logger.py`) and it works everywhere automatically!

## Step-by-Step Guide

### Step 1: Create Your Transport Class

Create a new file in `logiscout_logger/transports/`:

```python
# logiscout_logger/transports/your_transport.py

from .base import Transport
from ..events import LogEvent, RequestLogPayload
from typing import Dict, Any

class YourTransport(Transport):
    """
    Your custom transport implementation.
    """

    def __init__(self, **kwargs):
        """
        Initialize your transport with necessary configuration.

        Args:
            **kwargs: Any configuration your transport needs
                     (api_token, queue_url, connection_string, etc.)
        """
        # Initialize your transport here
        self._config = kwargs
        # Set up connections, clients, etc.

    def send(self, event: LogEvent) -> None:
        """
        Send a single log event.

        This is called for individual logs (legacy method).
        You can implement this or leave it as pass if you only
        support batch sending.

        Args:
            event: A single LogEvent object
        """
        # Implement single log sending
        pass

    def send_batch(self, payload: RequestLogPayload) -> None:
        """
        Send a single request's logs (one RequestLogPayload).

        This is called by the legacy BatchTransportProcessor.
        Implement this if you want to support per-request batching.

        Args:
            payload: A RequestLogPayload object (one request with multiple logs)
        """
        # Convert to dict
        payload_dict = payload.to_dict()

        # Send via your transport
        # Example: self._client.publish(payload_dict)
        pass

    def send_batch_of_batches(self, batch: Dict[str, Any]) -> None:
        """
        Send a batch of multiple RequestLogPayload objects.

        This is called by the BatchManager (intelligent batching system).
        This is the MOST IMPORTANT method to implement.

        Args:
            batch: Dictionary containing:
                - payloads: List[Dict] - List of RequestLogPayload dicts
                - batch_metadata: Dict - Metadata about the batch
                    - total_requests: int
                    - total_logs: int
                    - flushed_at: str (ISO timestamp)

        Example batch structure:
        {
            "payloads": [
                {
                    "correlationId": "abc-123",
                    "startedAt": "2026-02-09T10:30:00.000Z",
                    "endedAt": "2026-02-09T10:30:00.456Z",
                    "durationMS": 456.0,
                    "request": {...},
                    "logs": [...]
                }
            ],
            "batch_metadata": {
                "total_requests": 15,
                "total_logs": 200,
                "flushed_at": "2026-02-09T10:30:05.000Z"
            }
        }
        """
        # Implement batch sending via your transport
        # Example:
        # self._client.send(
        #     data=batch,
        #     headers={'Authorization': f'Bearer {self._api_token}'}
        # )
        pass

    def close(self) -> None:
        """
        Optional: Clean up resources on shutdown.
        Called when the application exits.
        """
        # Close connections, flush buffers, etc.
        pass
```

### Step 2: Export Your Transport

Add your transport to `logiscout_logger/transports/__init__.py`:

```python
from .console import ConsoleTransport
from .http import HTTPTransport
from .your_transport import YourTransport  # Add this

__all__ = [
    "Transport",
    "ConsoleTransport",
    "HTTPTransport",
    "YourTransport",  # Add this
]
```

### Step 3: Use Your Transport (ONE LINE CHANGE!)

In `logiscout_logger/logger.py`, find the `init()` function and replace the transport initialization:

```python
def init(
    *,
    endpoint: str = None,      # Make this optional
    api_token: str = None,     # Add new params as needed
    service_name: str,
    env: Environment,
):
    """
    Initialize LogiScout logger.
    Must be called once at app startup.
    """
    global _configured, _transport, _batch_transport_processor, _batch_manager

    with _lock:
        if _configured:
            return

        _config["endpoint"] = endpoint
        _config["service_name"] = service_name
        _config["environment"] = env.value if isinstance(env, Environment) else env

        # Initialize transport only if environment is PROD
        if env == Environment.PROD or env == "production":
            # OLD WAY - HTTP Transport
            # _transport = HTTPTransport(endpoint)

            # NEW WAY - Your Transport (ONLY CHANGE HERE!)
            from .transports.your_transport import YourTransport
            _transport = YourTransport(
                api_token=api_token,
                # ... any other config
            )

            # Create batch manager (automatically uses your transport!)
            _batch_manager = BatchManager(_transport, max_logs=200, max_wait_seconds=30.0)

            # Keep legacy processor for backward compatibility
            _batch_transport_processor = BatchTransportProcessor(_transport)

            # Register cleanup on exit
            atexit.register(_shutdown_batch_manager)

        _configure_structlog()
        _configured = True
```

### Step 4: Update User-Facing Init

Update the public init signature if you changed parameters:

```python
# User calls this
from logiscout_logger import init, PROD

init(
    api_token="sk_prod_...",  # New parameter
    service_name="my-service",
    env=PROD
)
```

## That's It!

**You only changed ONE file** (`logger.py`), and now:

✅ BatchManager uses your transport
✅ Middleware uses your transport
✅ All batching logic uses your transport
✅ No changes needed in:
   - batch_manager.py
   - configuration.py (middleware)
   - requestBuffer.py
   - Any other processors

## Real-World Example: RabbitMQ Transport

```python
# logiscout_logger/transports/rabbitmq.py

from .base import Transport
from ..events import LogEvent, RequestLogPayload
import pika
import json
from typing import Dict, Any

class RabbitMQTransport(Transport):
    """RabbitMQ transport for LogiScout logger"""

    def __init__(self, rabbitmq_url: str, api_token: str):
        self._api_token = api_token
        self._connection = pika.BlockingConnection(
            pika.URLParameters(rabbitmq_url)
        )
        self._channel = self._connection.channel()
        self._channel.queue_declare(queue='logiscout_logs', durable=True)

    def send_batch_of_batches(self, batch: Dict[str, Any]) -> None:
        """Send batch to RabbitMQ"""
        message = json.dumps(batch)

        self._channel.basic_publish(
            exchange='',
            routing_key='logiscout_logs',
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                headers={
                    'Authorization': f'Bearer {self._api_token}',
                    'Content-Type': 'application/json'
                }
            )
        )

    def close(self) -> None:
        """Close RabbitMQ connection"""
        if self._connection and not self._connection.is_closed:
            self._connection.close()
```

Then in `logger.py`:

```python
# Just change this ONE line in init():
_transport = RabbitMQTransport(
    rabbitmq_url="amqp://guest:guest@localhost:5672/",
    api_token=api_token
)
```

Done! The entire batching system now uses RabbitMQ! 🚀

## Testing Your Transport

Create a test file:

```python
# tests/test_your_transport.py

from logiscout_logger import init, get_logger, PROD
from logiscout_logger.logger import get_batch_manager
import time

def test_your_transport():
    init(
        api_token="test_token",
        service_name="test-service",
        env=PROD
    )

    logger = get_logger(__name__)

    # Generate some logs
    for i in range(50):
        logger.info(f"Test log {i}", test_data={"index": i})

    # Wait for batch to flush (30 seconds or 200 logs)
    time.sleep(35)

    # Verify logs were sent via your transport
    # Check your transport's destination (queue, db, etc.)

if __name__ == "__main__":
    test_your_transport()
```

## Backward Compatibility

The old `send()` and `send_batch()` methods are still supported:

- `send(event)` - For single log events (legacy)
- `send_batch(payload)` - For single request batch (legacy BatchTransportProcessor)
- `send_batch_of_batches(batch)` - For intelligent batching (new BatchManager)

You can implement all three or just the one you need. The base class provides default implementations that do nothing.

## Summary

| What | Where to Change |
|------|----------------|
| Add new transport | `logiscout_logger/transports/your_transport.py` |
| Switch transport | `logiscout_logger/logger.py` (ONE line in `init()`) |
| Everything else | **No changes needed!** |

The transport abstraction ensures that changing how logs are sent requires minimal code changes! 🎉
