# LogiScout Logger

Python logging library for ingesting logs into [LogiScout](https://github.com/Kazim68/logiscout-logger). Built on top of `structlog` to provide context-rich, structured logs with intelligent batching.

## Features

- **Structured Logging**: JSON-formatted logs with timestamps, levels, and metadata
- **Intelligent Batching**: Automatically batches logs (200 logs or 30 seconds) to reduce network overhead
- **Correlation ID Tracking**: Automatic request correlation across your application
- **Environment Support**: DEV (console only) and PROD (console + remote) modes
- **Confidential Logging**: Mark sensitive logs to prevent them from being sent remotely
- **Framework Support**: Built-in middleware for FastAPI, Flask, and other ASGI/WSGI frameworks

## Installation

```bash
pip install logiscout-logger
```

## Quick Start

### Basic Usage

```python
from logiscout_logger import init, get_logger, PROD, DEV

# Initialize the logger
init(
    endpoint="https://api.logiscout.com/logs",
    service_name="my-service",
    env=PROD  # Use DEV for local development (no remote sending)
)

# Get a logger instance
logger = get_logger(__name__)

# Log messages
logger.info("User logged in", user_id=123)
logger.warning("Rate limit approaching", current=95, limit=100)
logger.error("Payment failed", order_id="abc-123", reason="insufficient_funds")
```

### FastAPI Integration

```python
from fastapi import FastAPI
from logiscout_logger import init, get_logger, asgiConfiguration, PROD

app = FastAPI()

# Initialize LogiScout
init(
    endpoint="https://api.logiscout.com/logs",
    service_name="my-fastapi-app",
    env=PROD
)

# Add middleware for automatic correlation ID tracking
app.add_middleware(asgiConfiguration)

logger = get_logger("api")

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    logger.info("Fetching user", user_id=user_id)
    # Your logic here
    return {"user_id": user_id}
```

### Flask Integration

```python
from flask import Flask
from logiscout_logger import init, get_logger, wsgiConfiguration, PROD

app = Flask(__name__)

# Initialize LogiScout
init(
    endpoint="https://api.logiscout.com/logs",
    service_name="my-flask-app",
    env=PROD
)

# Apply WSGI middleware
app.wsgi_app = wsgiConfiguration(app.wsgi_app)

logger = get_logger("api")

@app.route("/users/<int:user_id>")
def get_user(user_id):
    logger.info("Fetching user", user_id=user_id)
    return {"user_id": user_id}
```

### Django Integration

**1. Initialize in `settings.py`:**

```python
from logiscout_logger import init, PROD, DEV

init(
    endpoint="https://api.logiscout.com/logs",
    service_name="my-django-app",
    env=PROD  # Use DEV for local development
)
```

**2. Apply middleware in `wsgi.py`:**

```python
import os
from django.core.wsgi import get_wsgi_application
from logiscout_logger import wsgiConfiguration

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

application = get_wsgi_application()
application = wsgiConfiguration(application)
```

If running Django with an ASGI server (e.g., Uvicorn), apply the middleware in `asgi.py` instead:

```python
import os
from django.core.asgi import get_asgi_application
from logiscout_logger import asgiConfiguration

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

application = get_asgi_application()
application = asgiConfiguration(application)
```

**3. Use in views:**

```python
from logiscout_logger import get_logger

logger = get_logger(__name__)

def my_view(request):
    logger.info("Processing request", user_id=request.user.id)
    return JsonResponse({"status": "ok"})
```

## Environment Modes

### Development Mode (DEV)

In DEV mode, logs are only printed to the console. No logs are sent to the remote endpoint.

```python
from logiscout_logger import init, DEV

init(
    endpoint="https://api.logiscout.com/logs",
    service_name="my-service",
    env=DEV  # Logs only go to console
)
```

### Production Mode (PROD)

In PROD mode, logs are printed to the console AND sent to the remote endpoint with intelligent batching.

```python
from logiscout_logger import init, PROD

init(
    endpoint="https://api.logiscout.com/logs",
    service_name="my-service",
    env=PROD  # Logs go to console AND remote
)
```

## Confidential Logging

For sensitive data that should not be sent to the remote server, use the `send=False` parameter:

```python
logger = get_logger(__name__)

# This log will be sent to the remote server
logger.info("User authenticated", user_id=123)

# This log will ONLY appear in the console (not sent remotely)
logger.info("Password reset token generated", token="secret-token", send=False)

# Works with all log levels
logger.debug("Sensitive debug info", data=sensitive_data, send=False)
logger.error("Internal error details", stack_trace=trace, send=False)
```

## Log Levels

```python
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical error message")
```

## Adding Metadata

Add any additional context to your logs:

```python
# Inline metadata
logger.info("Order created", order_id="123", total=99.99, currency="USD")

# Bound logger with persistent context
user_logger = logger.bind(user_id=123, session_id="abc")
user_logger.info("User action", action="click")  # Includes user_id and session_id
```

## Standalone Usage

You can use logiscout-logger without connecting to a remote service. Logs will only go to the console:

```python
from logiscout_logger import get_logger

# No init() call needed for console-only logging
logger = get_logger("my_script")

logger.info("Script started")
logger.debug("Processing data", count=100)
logger.warning("Disk space low", available_gb=1.5)
```

## API Reference

### `init()`

Initialize the LogiScout logger.

```python
init(
    endpoint: str,        # Remote logging endpoint URL
    service_name: str,    # Service identifier
    env: Environment      # DEV or PROD
)
```

### `get_logger()`

Get a logger instance.

```python
logger = get_logger(name: str)  # Usually __name__
```

### Logger Methods

```python
logger.debug(msg: str, send: bool = True, **kwargs)
logger.info(msg: str, send: bool = True, **kwargs)
logger.warning(msg: str, send: bool = True, **kwargs)
logger.error(msg: str, send: bool = True, **kwargs)
logger.critical(msg: str, send: bool = True, **kwargs)
```

### Middleware

```python
from logiscout_logger import asgiConfiguration, wsgiConfiguration

# For ASGI (FastAPI, Starlette, Django with ASGI)
app.add_middleware(asgiConfiguration)

# For WSGI (Flask, Django with WSGI)
app.wsgi_app = wsgiConfiguration(app.wsgi_app)
```

## Requirements

- Python 3.9+
- structlog >= 24.0.0
- requests >= 2.28.0

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- Issues: https://github.com/Kazim68/logiscout-logger/issues
