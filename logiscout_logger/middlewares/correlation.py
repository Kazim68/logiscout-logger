import uuid
import structlog

# --------------------------
# Helper Functions
# --------------------------

def asgi_handle_correlation_id(scope):
    """
    Handles correlation ID logic for ASGI:
    - Extracts from header or generates new ID
    - Injects back into headers if new
    - Binds to structlog context
    """
    correlation_id = None
    headers = list(scope.get("headers", []))

    # Try to find existing ID
    for name, value in headers:
        if name.lower() == b"x-correlation-id":
            try:
                correlation_id = value.decode("ascii")
                break
            except UnicodeDecodeError:
                pass

    # Generate if missing
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
        # Inject into headers
        headers.append((b"x-correlation-id", correlation_id.encode("ascii")))
        scope["headers"] = headers

    # Bind to context
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    return correlation_id


def wsgi_handle_correlation_id(environ):
    """
    Handles correlation ID logic for WSGI:
    - Extracts from environ or generates new ID
    - Injects back into environ
    - Binds to structlog context
    """
    correlation_id = environ.get("HTTP_X_CORRELATION_ID")

    if not correlation_id:
        correlation_id = str(uuid.uuid4())
        environ["HTTP_X_CORRELATION_ID"] = correlation_id

    # Set specific key
    environ["logiscout.correlation_id"] = correlation_id

    # Bind to context
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    return correlation_id

