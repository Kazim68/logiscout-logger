# LogiScout Logger

A robust structured logging library for Python that seamlessly integrates with the LogiScout service. It uses `structlog` under the hood to provide context-rich, JSON-formatted logs.

## Installation

```bash
pip install logiscout-logger
```

## Usage

### 1. With LogiScout Service (Remote Logging)

If you are sending logs to a LogiScout instance, you must initialize the library with your endpoint and service name at the startup of your application. You also need to configure the middleware to handle correlation IDs automatically.

#### Initialization & Middleware (FastAPI Example)

```python
from fastapi import FastAPI
from logiscout_logger import init, get_logger, asgiConfiguration

app = FastAPI()

# 1. Initialize LogiScout
# This configures the remote transport to send logs to your LogiScout instance.
init(
    service_name="my-fastapi-app",
    endpoint="https://logiscout.example.com/logs"
)

# 2. Add this middleware to capture context rich logs
app.add_middleware(asgiConfiguration)
logger = get_logger("service-name")

@app.get("/")
def read_root():
    return {"Hello": "World"}
```

#### Middleware for WSGI (Flask/Django)

For synchronous frameworks like Flask or Django, use the `wsgiConfiguration` middleware.

**Flask Example:**

```python
from flask import Flask
from logiscout_logger import init, get_logger, wsgiConfiguration

app = Flask(__name__)

init(
    service_name="my-flask-app",
    endpoint="https://logiscout.example.com/logs"
)

# Apply WSGI middleware
app.wsgi_app = wsgiConfiguration(app.wsgi_app)
```

#### Logging in your code

Once initialized, use `get_logger` anywhere in your application.

```python
from logiscout_logger import get_logger

logger = get_logger(__name__)

def process_payment(amount: float):
    # Logs will include timestamp, log level, service name, and correlation ID (if in a request)
    logger.info("Processing payment", amount=amount, currency="USD")

    try:
        # ... logic ...
        logger.info("Payment successful")
    except Exception as e:
        # Automatically formats exception tracebacks
        logger.error("Payment failed", error=str(e))
```

### 2. Standalone Usage (Local Logging)

You can use `logiscout-logger` as a standard logging library without connecting to the LogiScout service. In this mode, it outputs structured logs to the console/stdout.

You do **not** need to call `init()` or set up an endpoint.

```python
from logiscout_logger import get_logger

# Calls safely fallback to console logging if init() wasn't called
logger = get_logger("my_script")

logger.info("Script started")

user_id = 42
logger.debug("Fetching user data", user_id=user_id)

logger.warning("Disk space low", available_gb=1.5)
```
