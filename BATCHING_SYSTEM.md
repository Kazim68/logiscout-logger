# LogiScout Intelligent Batching System

## Overview

The LogiScout logger ships with an intelligent batching system that efficiently groups request log payloads before sending them to the LogiScout ingest endpoint. This reduces network overhead, smooths out spiky traffic, and keeps client-side resource usage predictable.

## How It Works

### Batching Strategy

The system uses two triggers to decide when to send a batch:

1. **Log Count Threshold**: Flush the batch when the total number of log entries across all queued request payloads reaches **200 logs**.
2. **Time-Based Flushing**: Flush the batch every **30 seconds** regardless of log count, as long as there is at least one queued payload.

Whichever trigger fires first wins.

### Key Features

#### 1. Smart Log Counting
- Counts log entries across all queued request payloads, not request payloads themselves.
- A single request may produce many log entries; the manager tracks the cumulative log count across all queued requests.

#### 2. Partial Payload Handling
When adding a payload would push the batch above the 200-log limit:
- Logs are split: the first slice fills the batch up to exactly 200 logs and is sent.
- The remaining logs from the same request are kept in a residual payload (same `correlationId`, `request`, timestamps) and carried over into the next batch.
- The backend can stitch the slices back together by `correlationId`.

#### 3. Incomplete Request Handling
For requests that are still in progress when a batch is flushed:
- Whatever has been buffered so far (correlationId, startedAt, partial logs, etc.) gets sent.
- When the request finishes, the middleware submits the final payload and it goes out in a later batch.
- The backend merges the partial and final payloads using `correlationId`.

#### 4. Thread-Safe Operation
- All mutations of the batch state are guarded by a `threading.Lock`.
- A daemon background thread (`LogiScout-BatchFlusher`) handles the time-based flush.
- Safe to use from concurrent ASGI/WSGI workers in the same process.

#### 5. Graceful Shutdown
- `BatchManager.shutdown()` stops the background thread and performs a final flush.
- It is registered with `atexit` during `init()`, so any remaining payloads are flushed when the process exits cleanly.

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
│  - Hands the assembled RequestLogPayload to the BatchManager │
│    when the request ends                                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              BatchManager (Processor)                        │
│  Location: logiscout_logger/processors/batch_manager.py      │
│                                                               │
│  State:                                                       │
│  - Current batch:    List[dict] (serialized payloads)        │
│  - Total log count:  int                                     │
│  - Last flush time:  timestamp                               │
│                                                               │
│  Triggers:                                                    │
│  - Log count >= 200  →  Immediate flush (caller thread)      │
│  - Time  >= 30 sec   →  Background flush                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Transport (Abstract)                       │
│  Location: logiscout_logger/transports/base.py               │
│                                                               │
│  Methods:                                                     │
│  - send(event)                 → Single log                  │
│  - send_batch(payload)         → Single request payload      │
│  - send_batch_of_batches(...)  → Batch of request payloads   │
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
         │  - Bearer auth  │  │  - Kafka         │
         │  - JSON payload │  │                  │
         └─────────────────┘  └──────────────────┘
```

### Key Design Benefits

1. **Single Point of Change**: Swapping the transport in `logger.py` automatically propagates everywhere.
2. **Transport Abstraction**: The `BatchManager` calls the generic `send_batch_of_batches()` method, so it doesn't care whether the transport is HTTP, a queue, etc.
3. **Easy Extension**: New transports just implement the `Transport` base interface.
4. **Processor Pattern**: The `BatchManager` lives under `logiscout_logger/processors/`, in line with the rest of the library's architecture.

### Batch Format (wire payload)

The current implementation sends a JSON object with a single `payloads` array:

```json
{
  "payloads": [
    {
      "correlationId": "abc-123",
      "startedAt": "2026-04-25T10:30:00.000Z",
      "endedAt": "2026-04-25T10:30:00.456Z",
      "durationMS": 456.0,
      "request": {
        "method": "GET",
        "path": "/api/users",
        "statusCode": 200
      },
      "logs": [
        {
          "timestamp": "2026-04-25T10:30:00.100Z",
          "level": "info",
          "message": "Processing request",
          "loggerName": "app",
          "metadata": {}
        }
      ]
    }
  ]
}
```

> Note: an optional `batch_metadata` block (with `total_requests`, `total_logs`, `flushed_at`) is computed inside the manager but is currently not included in the outgoing payload. It can be re-enabled in `batch_manager.py::_flush_batch()` if the backend wants it.

## Configuration

### Initialization

```python
from logiscout_logger import init, PROD

init(
    api_token="your_api_key",
    service_name="my-service",
    env=PROD,  # Batching only activates in PROD
)
```

In `DEV`, no transport or batch manager is created — logs only go to the console.

### Custom Thresholds

The batch manager is constructed inside `init()`. To tune the thresholds, edit the construction in `logger.py`:

```python
# logiscout_logger/logger.py
_batch_manager = BatchManager(
    _transport,
    max_logs=200,         # log-count threshold
    max_wait_seconds=30.0 # time-based threshold (seconds)
)
```

## Usage Examples

### Example 1: Normal Operation

```python
# During request handling, logs are buffered per-request via the middleware
logger.info("User logged in", user_id=123)
logger.debug("Validating token", token_hash="abc...")

# On request completion, the middleware builds a RequestLogPayload
# and calls batch_manager.add_payload(payload). The manager either
# accumulates or flushes depending on thresholds.
```

### Example 2: High-Volume Scenario

```
Request 1: 50 logs   → Added to batch (total: 50)
Request 2: 75 logs   → Added to batch (total: 125)
Request 3: 80 logs   → Added to batch (total: 205)
                     → FLUSH! Sends a batch with the first 200 logs
                       (Request 3's logs are split: 75 sent, 5 carried over)
                     → 5 logs from Request 3 remain queued for the next batch
```

### Example 3: Low-Volume Scenario

```
Request 1: 10 logs  → Added to batch (total: 10)
Request 2: 15 logs  → Added to batch (total: 25)
... 30 seconds pass ...
                    → Background thread flushes (time-based trigger)
```

## Performance Considerations

### Benefits
- **Fewer network calls**: Many requests collapse into a single HTTP POST.
- **Lower request latency**: Application requests don't wait on per-log network I/O.
- **Bounded memory**: The 200-log cap keeps batch size predictable.
- **Async-friendly**: The background thread handles timed flushes without blocking application code.

### Resource Usage
- **Memory**: ~200 log entries × ~1KB each ≈ ~200KB max per batch (typical).
- **Threads**: +1 daemon thread (`LogiScout-BatchFlusher`) for time-based flushing.
- **Network**: One HTTP POST per flush — at most every ~30 seconds in steady state, more often under load.

## Authentication

`HTTPTransport` sends an `Authorization: Bearer <api_token>` header on every request. The token is supplied to `init()` and stored on the transport instance. There is no token refresh — the token is used as-is.

## Future Enhancements

### Queue-Based Transport
A future implementation may swap HTTP for a message queue. Example sketch:

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
        ...

    def send_batch(self, payload: RequestLogPayload) -> None:
        ...

    def send_batch_of_batches(self, batch: dict) -> None:
        self._channel.basic_publish(
            exchange='logs',
            routing_key='batch',
            body=json.dumps(batch),
            properties=pika.BasicProperties(
                headers={'Authorization': f'Bearer {self._api_token}'}
            )
        )
```

To use it, change one line in `logger.py::init()`:

```python
# Old: HTTP transport
_transport = HTTPTransport(_ENDPOINT_URL, api_token)

# New: Queue transport
_transport = QueueTransport(queue_url="amqp://...", api_token=api_token)
```

The `BatchManager` and middleware require no changes — the transport is fully abstracted.

## Troubleshooting

### Logs Not Being Sent
1. Verify the environment is `PROD`. In `DEV`, no transport is created.
2. Verify `get_batch_manager()` returns a non-`None` value.
3. Confirm logs reach the 200-count threshold or wait at least 30 seconds.
4. Check the LogiScout endpoint is reachable from the host.

### Memory Issues
- Lower `max_logs` to flush smaller batches more often.
- Lower `max_wait_seconds` to flush more frequently regardless of volume.

### Missing Logs on Shutdown
- Ensure the process exits cleanly so the `atexit` handler runs.
- For abrupt termination (SIGKILL, container OOM), call `get_batch_manager().shutdown()` from your own shutdown hook.

## API Reference

### BatchManager

```python
class BatchManager:
    def __init__(self, transport, max_logs: int = 200, max_wait_seconds: float = 30.0):
        """Initialize the batch manager with the configured thresholds."""

    def add_payload(self, payload: RequestLogPayload) -> None:
        """Add a payload to the batch (may trigger an immediate flush)."""

    def flush(self) -> None:
        """Manually flush the current batch."""

    def shutdown(self) -> None:
        """Stop the background thread and perform a final flush."""
```

### Helper Functions

```python
def get_batch_manager() -> Optional[BatchManager]:
    """Return the global batch manager instance (or None in DEV)."""

def get_batch_transport_processor() -> Optional[BatchTransportProcessor]:
    """Return the legacy single-payload processor. Deprecated — prefer get_batch_manager()."""
```
