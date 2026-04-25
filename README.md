<div align="center">

# LogiScout Logger

**Structured logging for Python services, with intelligent batching and zero-config request correlation.**

[![PyPI version](https://img.shields.io/pypi/v/logiscout-logger.svg)](https://pypi.org/project/logiscout-logger/)
[![Python versions](https://img.shields.io/pypi/pyversions/logiscout-logger.svg)](https://pypi.org/project/logiscout-logger/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/logiscout-logger.svg)](https://pypi.org/project/logiscout-logger/)

[Installation](#installation) ·
[Quick Start](#quick-start) ·
[Integrations](#framework-integrations) ·
[API Reference](#api-reference) ·
[Batching](#batching)

</div>

---

## Overview

`logiscout-logger` is a Python logging client for the [LogiScout](https://github.com/Kazim68/logiscout-logger) ingest platform. It is built on top of [`structlog`](https://www.structlog.org/) and ships with first-class support for FastAPI, Flask, and Django — including automatic per-request correlation IDs and an intelligent batching layer that minimizes network overhead.

If you're already using `structlog`, the API will feel familiar. If you're not, the learning curve is small: `init()` once at startup, `get_logger(__name__)` everywhere else.

## Highlights

-  **Structured by default** — every log carries a timestamp, level, logger name, and arbitrary metadata as JSON.
-  **Intelligent batching** — payloads are flushed when **200 logs** accumulate or **30 seconds** elapse, whichever comes first.
-  **Automatic correlation** — middleware tags every log emitted during a request with the same `correlationId`.
-  **Framework-ready** — drop-in middleware for ASGI (FastAPI, Starlette, Django ASGI) and WSGI (Flask, Django WSGI).
-  **DEV / PROD modes** — console-only in development, console + batched remote ingest in production.
-  **Confidential logs** — flag sensitive entries with `send=False` so they never leave the host.
-  **Thread-safe** — designed for concurrent web workers and high-throughput services.
-  **Graceful shutdown** — remaining logs are flushed automatically on process exit.

## Installation

```bash
pip install logiscout-logger
```

**Requirements**

| Dependency | Version |
| ---------- | ------- |
| Python     | `>= 3.9` |
| structlog  | `>= 24.0.0` |
| requests   | `>= 2.28.0` |

## Quick Start

```python
from logiscout_logger import init, get_logger, PROD

# 1. Initialize once at app startup
init(
    api_token="your_api_key",
    service_name="my-service",
    env=PROD,
)

# 2. Get a logger anywhere in your codebase
logger = get_logger(__name__)

# 3. Log structured events
logger.info("User logged in", user_id=123)
logger.warning("Rate limit approaching", current=95, limit=100)
logger.error("Payment failed", order_id="abc-123", reason="insufficient_funds")
```

In `DEV` mode the same code prints to the console only — no network calls, no token required.

## Framework Integrations

### FastAPI

```python
from fastapi import FastAPI
from logiscout_logger import init, get_logger, asgiConfiguration, PROD

app = FastAPI()

init(api_token="your_api_key", service_name="my-fastapi-app", env=PROD)
app.add_middleware(asgiConfiguration)

logger = get_logger("api")

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    logger.info("Fetching user", user_id=user_id)
    return {"user_id": user_id}
```

### Flask

```python
from flask import Flask
from logiscout_logger import init, get_logger, wsgiConfiguration, PROD

app = Flask(__name__)

init(api_token="your_api_key", service_name="my-flask-app", env=PROD)
app.wsgi_app = wsgiConfiguration(app.wsgi_app)

logger = get_logger("api")

@app.route("/users/<int:user_id>")
def get_user(user_id):
    logger.info("Fetching user", user_id=user_id)
    return {"user_id": user_id}
```

### Django

**1. Initialize in `settings.py`:**

```python
from logiscout_logger import init, PROD

init(api_token="your_api_key", service_name="my-django-app", env=PROD)
```

**2. Apply middleware in `wsgi.py`:**

```python
import os
from django.core.wsgi import get_wsgi_application
from logiscout_logger import wsgiConfiguration

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

application = get_wsgi_application()
application = wsgiConfiguration(application)
```

For ASGI deployments (e.g. Uvicorn, Daphne), apply `asgiConfiguration` in `asgi.py` instead:

```python
import os
from django.core.asgi import get_asgi_application
from logiscout_logger import asgiConfiguration

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

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

| Mode  | Console output | Remote ingest | Batching | Notes |
| ----- | :------------: | :-----------: | :------: | ----- |
| `DEV` |       ✔        |       ✘       |    ✘     | Ideal for local development. No `api_token` required. |
| `PROD`|       ✔        |       ✔       |    ✔     | Logs are batched and shipped to the LogiScout endpoint. |

```python
from logiscout_logger import init, DEV, PROD

# Development — console only
init(api_token="...", service_name="my-service", env=DEV)

# Production — console + remote with batching
init(api_token="...", service_name="my-service", env=PROD)
```

## Logging API

### Levels

```python
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical error message")
```

### Adding Metadata

Pass arbitrary keyword arguments — they are serialized into the structured log entry:

```python
logger.info("Order created", order_id="123", total=99.99, currency="USD")
```

### Bound Loggers

Bind context once and reuse it across calls:

```python
user_logger = logger.bind(user_id=123, session_id="abc")
user_logger.info("User action", action="click")  # includes user_id and session_id
```

### Confidential Logging

Use `send=False` to keep a log local to the host (still printed to the console, never transmitted):

```python
logger.info("Password reset token generated", token="secret-token", send=False)
logger.error("Internal error details", stack_trace=trace, send=False)
```

This works on every level (`debug`, `info`, `warning`, `error`, `critical`).

## Standalone Usage

The library can be used as a plain console logger without calling `init()`:

```python
from logiscout_logger import get_logger

logger = get_logger("my_script")
logger.info("Script started")
logger.warning("Disk space low", available_gb=1.5)
```

Nothing is sent to the network in this mode.

## Batching

In `PROD`, request payloads are queued and flushed by the `BatchManager`:

- **Log-count trigger** — flushes when total queued logs reach **200**.
- **Time trigger** — flushes every **30 seconds** as long as the queue is non-empty.
- **Partial payloads** — large requests are split across batches and re-stitched on the backend by `correlationId`.
- **Graceful shutdown** — `atexit` flushes any remaining logs on a clean process exit.

For the full design, batch wire format, and tuning knobs, see [`BATCHING_SYSTEM.md`](BATCHING_SYSTEM.md).

## API Reference

### `init(api_token, service_name, env)`

Initialize the LogiScout logger. Call once at app startup.

| Parameter      | Type          | Description |
| -------------- | ------------- | ----------- |
| `api_token`    | `str`         | API token for authenticating with the LogiScout ingest endpoint. |
| `service_name` | `str`         | Service identifier — applied to every log produced in this process. |
| `env`          | `Environment` | `DEV` (console only) or `PROD` (console + batched remote ingest). |

### `get_logger(name)`

Return a logger instance.

```python
logger = get_logger(__name__)
```

### `LogiScoutLogger`

```python
logger.debug(msg: str, send: bool = True, **metadata)
logger.info(msg: str, send: bool = True, **metadata)
logger.warning(msg: str, send: bool = True, **metadata)
logger.error(msg: str, send: bool = True, **metadata)
logger.critical(msg: str, send: bool = True, **metadata)
logger.bind(**context) -> LogiScoutLogger
```

### Middleware

```python
from logiscout_logger import asgiConfiguration, wsgiConfiguration

# ASGI — FastAPI, Starlette, Django (ASGI)
app.add_middleware(asgiConfiguration)

# WSGI — Flask, Django (WSGI)
app.wsgi_app = wsgiConfiguration(app.wsgi_app)
```

## How It Works

```
┌────────────────────┐    ┌─────────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Application code  │ →  │   structlog chain   │ →  │   BatchManager   │ →  │   HTTPTransport  │
│  logger.info(...)  │    │ build_log_event,    │    │  200 logs / 30s  │    │   POST /ingest   │
│                    │    │ push_to_buffer, …   │    │  thread-safe     │    │   Bearer auth    │
└────────────────────┘    └─────────────────────┘    └──────────────────┘    └──────────────────┘
            │                                                                           ▲
            │                                                                           │
            └──────── ASGI / WSGI middleware adds correlationId ────────────────────────┘
```

## Contributing

Issues and pull requests are welcome. Please open an issue first for non-trivial changes so we can align on direction.

1. Fork the repository.
2. Create a feature branch.
3. Run the test suite (`pytest`).
4. Submit a pull request describing the change and its motivation.

## License

[MIT](LICENSE) © Abdur Rehman Kazim

## Links

- **PyPI**: https://pypi.org/project/logiscout-logger/
- **Source**: https://github.com/Kazim68/logiscout-logger
- **Issues**: https://github.com/Kazim68/logiscout-logger/issues
- **Batching design**: [`BATCHING_SYSTEM.md`](BATCHING_SYSTEM.md)
