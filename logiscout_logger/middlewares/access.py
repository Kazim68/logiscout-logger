import time
import structlog

# --------------------------
# Helper Functions
# --------------------------

def bind_access_context(method, path, status_code=None, duration=None):
    """
    Binds HTTP method and path to structlog context variables.
    Optionally binds status_code and duration when available.
    Duration is expected in milliseconds.
    """
    context = {
        "http_method": method,
        "url_path": path,
    }
    if status_code is not None:
        context["status_code"] = status_code
    if duration is not None:
        context["duration_ms"] = duration
    structlog.contextvars.bind_contextvars(**context)

def log_access_entry(logger, method, path, status_code, duration):
    """
    Logs the final access log entry.
    Binds statu`s_code and duration to context vars first, then logs.
    """
    bind_access_context(method, path, status_code, duration)
    logger.info("Access Log")
