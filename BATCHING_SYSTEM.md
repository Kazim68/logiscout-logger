# LogiScout Intelligent Batching System

## Overview

The LogiScout logger now includes an intelligent batching system that efficiently manages request log payloads before sending them to the backend. This reduces network overhead and optimizes resource usage on the client side.

## How It Works

### Batching Strategy

The system uses two triggers to decide when to send batches:

1. **Log Count Threshold**: Sends batch when total logs across all payloads reach **200 logs**
2. **Time-Based Flushing**: Sends batch every **30 seconds** regardless of log count

### Key Features

#### 1. **Smart Log Counting**
- Counts logs across all request payloads in the batch
- One request payload may contain many logs
- System tracks cumulative log count

#### 2. **Partial Payload Handling**
When a request payload would exceed the 200-log limit:
- Sends the first 200 logs (may split a single request's logs)
- Remaining logs are kept for the next batch
- Each batch respects the 200-log limit to control client resource usage

#### 3. **Incomplete Request Handling**
For requests that are still in progress when a batch is sent:
- Sends available data (correlationId, startedAt, partial logs, etc.)
- When request completes, sends updated payload in next batch
- Backend can merge these payloads using correlationId

#### 4. **Thread-Safe Operation**
- Uses threading locks for concurrent request handling
- Background thread manages time-based flushing
- Safe for high-concurrency web applications

#### 5. **Graceful Shutdown**
- Automatically flushes remaining logs on application exit
- Registered with Python's `atexit` module
- Ensures no log loss on shutdown

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                      Web Request                             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Middleware Layer                           │
│  (asgiConfiguration / wsgiConfiguration)                     │
│                                                               │
│  - Captures request metadata                                 │
│  - Buffers logs during request                               │
│  - Flushes to BatchManager on request end                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              BatchManager (Processor)                        │
│  Location: logiscout_logger/processors/batch_manager.py     │
│                                                               │
│  State:                                                       │
│  - Current batch: List[RequestLogPayload]                    │
│  - Total log count: int                                      │
│  - Last flush time: timestamp                                │
│                                                               │
│  Triggers:                                                    │
│  - Log count >= 200  →  Immediate flush                      │
│  - Time >= 30 sec    →  Background flush                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Transport (Abstract)                       │
│  Location: logiscout_logger/transports/base.py              │
│                                                               │
│  Methods:                                                     │
│  - send(event)                 → Single log                  │
│  - send_batch(payload)         → Single request batch        │
│  - send_batch_of_batches(...)  → Multiple requests batch     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                   ┌────────┴────────┐
                   │                 │
                   ▼                 ▼
         ┌─────────────────┐  ┌──────────────────┐
         │  HTTPTransport  │  │  Future: Queue   │
         │                 │  │     Transport    │
         │  Implements:    │  │                  │
         │  - HTTP POST    │  │  - RabbitMQ      │
         │  - JSON payload │  │  - Kafka         │
         └─────────────────┘  └──────────────────┘
```

### Key Design Benefits

1. **Single Point of Change**: Changing transport in `logger.py` automatically works everywhere
2. **Transport Abstraction**: BatchManager uses generic `send_batch_of_batches()` method
3. **Easy Extension**: New transports (Queue, Kafka, etc.) just implement the base Transport interface
4. **Processor Pattern**: BatchManager is a processor, following the library's architecture

### Batch Format

```json
{
  "payloads": [
    {
      "correlationId": "abc-123",
      "startedAt": "2026-02-09T10:30:00.000Z",
      "endedAt": "2026-02-09T10:30:00.456Z",
      "durationMS": 456.0,
      "request": {
        "method": "GET",
        "path": "/api/users",
        "statusCode": 200
      },
      "logs": [
        {
          "timestamp": "2026-02-09T10:30:00.100Z",
          "level": "info",
          "message": "Processing request",
          "logger_name": "app",
          "metadata": {}
        }
      ]
    }
  ],
  "batch_metadata": {
    "total_requests": 15,
    "total_logs": 200,
    "flushed_at": "2026-02-09T10:30:05.000Z"
  }
}
```

## Configuration

### Initialization

```python
from logiscout_logger import init, PROD

init(
    endpoint="https://api.logiscout.com/logs",
    service_name="my-service",
    env=PROD  # Batching only works in PROD environment
)
```

### Custom Configuration

The batch manager can be initialized with custom thresholds:

```python
# In logger.py init() function
_batch_manager = BatchManager(
    _transport,
    max_logs=200,        # Custom log count threshold
    max_wait_seconds=30.0  # Custom time threshold
)
```

## Usage Examples

### Example 1: Normal Operation

```python
# During request handling, logs are buffered
logger.info("User logged in", user_id=123)
logger.debug("Validating token", token_hash="abc...")

# At request end, middleware flushes to batch manager
# Batch manager accumulates payloads until threshold reached
```

### Example 2: High-Volume Scenario

```
Request 1: 50 logs   → Added to batch (total: 50)
Request 2: 75 logs   → Added to batch (total: 125)
Request 3: 80 logs   → Added to batch (total: 205)
                     → FLUSH! Sends first 200 logs
                     → Keeps remaining 5 logs for next batch
```

### Example 3: Low-Volume Scenario

```
Request 1: 10 logs  → Added to batch (total: 10)
Request 2: 15 logs  → Added to batch (total: 25)
... 30 seconds pass ...
                    → FLUSH! Time-based trigger
```

## Performance Considerations

### Benefits
- **Reduced Network Calls**: Batches multiple requests into one HTTP call
- **Lower Latency**: Requests don't wait for individual log sends
- **Resource Control**: 200-log limit prevents excessive memory usage
- **Better Throughput**: Background thread handles flushing asynchronously

### Resource Usage
- **Memory**: ~200 log entries × ~1KB each = ~200KB maximum batch size
- **Thread Count**: +1 background thread for time-based flushing
- **Network**: Batch sent every 30 seconds or 200 logs (whichever comes first)

## Future Enhancements

### Planned for API Token Implementation
When switching from endpoint to API token:
- Remove `endpoint` parameter
- Add `api_token` parameter
- Implement token-based authentication in transport
- Add token validation and refresh logic

```python
# Future API
init(
    api_token="sk_prod_...",
    service_name="my-service",
    env=PROD
)
```

### Queue-Based Transport
Future implementation will use message queues. Example:

```python
# logiscout_logger/transports/queue.py
from .base import Transport
from ..events import LogEvent, RequestLogPayload
import pika  # RabbitMQ example

class QueueTransport(Transport):
    def __init__(self, queue_url: str, api_token: str):
        self._queue_url = queue_url
        self._api_token = api_token
        self._connection = pika.BlockingConnection(...)
        self._channel = self._connection.channel()

    def send(self, event: LogEvent) -> None:
        # Implement single log send
        pass

    def send_batch(self, payload: RequestLogPayload) -> None:
        # Implement single request batch send
        pass

    def send_batch_of_batches(self, batch: dict) -> None:
        # Implement multiple requests batch send
        self._channel.basic_publish(
            exchange='logs',
            routing_key='batch',
            body=json.dumps(batch),
            properties=pika.BasicProperties(
                headers={'Authorization': f'Bearer {self._api_token}'}
            )
        )
```

To use it, simply change one line in your app:

```python
# Old: HTTP Transport
from logiscout_logger.transports.http import HTTPTransport
init(endpoint="http://...", service_name="...", env=PROD)

# New: Queue Transport - ONLY CHANGE IN logger.py
from logiscout_logger.transports.queue import QueueTransport

# In logger.py init():
_transport = QueueTransport(queue_url="amqp://...", api_token="sk_prod_...")
_batch_manager = BatchManager(_transport, max_logs=200, max_wait_seconds=30.0)

# BatchManager automatically uses the new transport!
# No changes needed in:
# - middleware
# - batch_manager
# - processors
# - buffer
```

## Troubleshooting

### Logs Not Being Sent
1. Verify environment is PROD: `env=PROD`
2. Check batch manager is initialized: `get_batch_manager() is not None`
3. Ensure logs reach 200 count or 30-second timeout

### Memory Issues
- Reduce `max_logs` threshold if memory constrained
- Reduce `max_wait_seconds` to flush more frequently

### Missing Logs on Shutdown
- Ensure graceful shutdown is working
- Check if `atexit` handlers are being called
- Manually call `batch_manager.flush()` before exit if needed

## API Reference

### BatchManager

```python
class BatchManager:
    def __init__(self, transport, max_logs=200, max_wait_seconds=30.0):
        """Initialize batch manager with thresholds"""

    def add_payload(self, payload: RequestLogPayload) -> None:
        """Add a payload to batch (may trigger flush)"""

    def flush(self) -> None:
        """Manually flush current batch"""

    def shutdown(self) -> None:
        """Shutdown and flush remaining data"""
```

### Helper Functions

```python
def get_batch_manager() -> Optional[BatchManager]:
    """Get the global batch manager instance"""

def get_batch_transport_processor() -> Optional[BatchTransportProcessor]:
    """Get legacy processor (deprecated)"""
```
