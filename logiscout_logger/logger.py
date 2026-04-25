from .transports.http import HTTPTransport
from .processors import (
    build_log_event,
    remove_internal_fields,
    filter_info_and_above,
    TransportProcessor,
    BatchTransportProcessor,
    BatchManager,
    push_to_request_buffer
)
import structlog
from structlog.contextvars import merge_contextvars
import threading
import logging
from enum import Enum
import atexit


# ------------------------
# Environment Enum
# ------------------------

class Environment(Enum):
    """Environment enum for LogiScout logger."""
    DEV = "development"
    PROD = "production"


# Convenience exports
DEV = Environment.DEV
PROD = Environment.PROD

# ------------------------
# Global configuration
# ------------------------

# Hardcoded remote logging endpoint
_ENDPOINT_URL = "http://localhost:3000/ingest"#"http://47.130.208.43:3000/ingest"

_config = {
    "api_token": None,
    "service_name": None,
    "environment": None,
}

_configured = False
_lock = threading.Lock()
_transport = None  # Single transport instance (HTTP, Console, etc.)
_batch_transport_processor = None  # Legacy processor for batched payloads
_batch_manager = None  # New intelligent batch manager


# ------------------------
# Public init()
# ------------------------

def init(
    *,
    api_token: str,
    service_name: str,
    env: Environment,
):
    """
    Initialize LogiScout logger.
    Must be called once at app startup.

    Args:
        api_token: The API token used to authenticate with the LogiScout endpoint
        service_name: Global service identifier (same for entire application)
        env: Environment (DEV or PROD)
    """
    global _configured, _transport, _batch_transport_processor, _batch_manager

    with _lock:
        if _configured:
            return

        _config["api_token"] = api_token
        _config["service_name"] = service_name
        _config["environment"] = env.value if isinstance(env, Environment) else env

        # Initialize transport only if an api_token is configured AND environment is PROD
        if api_token and (env == Environment.PROD or env == "production"):
            _transport = HTTPTransport(_ENDPOINT_URL, api_token)
            # Create batch manager with intelligent batching (200 logs or 30 seconds)
            _batch_manager = BatchManager(_transport, max_logs=200, max_wait_seconds=30.0)
            # Also keep legacy processor for backward compatibility
            _batch_transport_processor = BatchTransportProcessor(_transport)

            # Register cleanup on exit
            atexit.register(_shutdown_batch_manager)

        _configure_structlog()

        _configured = True

# ------------------------
# Structlog configuration
# ------------------------

def _configure_structlog():
    """
    Configure structlog for console output.
    """

    logging.basicConfig(level=logging.INFO, format="%(message)s")     # this shows logs with log levels of DEBUG or above

    # Build processor list
    processors = [
        merge_contextvars,  # Must be first - injects contextvars into log
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,

        # --- remote pipeline ---
        build_log_event,
        push_to_request_buffer,  # Push log to buffer if in request context
    ]

    # Note: HTTP transport is no longer added here per-log
    # Instead, it will be used by middleware to send batched payloads

    processors.extend([
        remove_internal_fields,     # cleanup before console output

        # --- console pipeline ---
        structlog.dev.ConsoleRenderer(),
    ])

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


# ------------------------
# get_logger()
# ------------------------

def get_logger(name: str):
    """
    Returns a LogiScout logger instance.

    Args:
        name: Logger name to identify this logger (e.g., module name).
              Different logger names allow you to distinguish between
              different modules in a large app. All loggers share the
              same service_name and endpoint configured in init().
    """
    if not _configured:
        # Safe fallback
        _configure_structlog()

    base_logger = structlog.get_logger(name)
    return LogiScoutLogger(base_logger)


def get_service_name() -> str:
    """
    Returns the configured service name.
    """
    return _config.get("service_name", "unknown-service")


def get_environment() -> str:
    """
    Returns the configured environment.
    """
    return _config.get("environment", "unknown")


def is_production() -> bool:
    """
    Returns True if the environment is PROD.
    """
    env = _config.get("environment")
    return env == "production"


def get_batch_transport_processor():
    """
    Returns the batch transport processor for middleware use.
    This processor handles sending batched RequestLogPayload objects.

    DEPRECATED: Use get_batch_manager() for intelligent batching.
    This function is kept for backward compatibility.

    Returns:
        BatchTransportProcessor instance or None if not configured
    """
    return _batch_transport_processor


def get_batch_manager():
    """
    Returns the batch manager for middleware use.
    The batch manager handles intelligent batching with:
    - 200 logs threshold
    - 30 seconds time-based flushing

    Returns:
        BatchManager instance or None if not configured
    """
    return _batch_manager


def _shutdown_batch_manager():
    """
    Internal function to shutdown batch manager on exit.
    Registered with atexit to ensure clean shutdown.
    """
    global _batch_manager
    if _batch_manager:
        _batch_manager.shutdown()


# ------------------------
# Logger wrapper
# ------------------------

class LogiScoutLogger:
    """
    Thin wrapper over structlog logger.
    """

    def __init__(self, logger):
        self._logger = logger

    # ---- Standard levels ----

    def debug(self, msg: str, send: bool = True, **kwargs):
        """
        Log a debug message.

        Args:
            msg: The log message
            send: If False, log will not be sent over HTTP (default: True)
            **kwargs: Additional metadata to include in the log
        """
        self._logger.debug(msg, _send=send, **kwargs)

    def info(self, msg: str, send: bool = True, **kwargs):
        """
        Log an info message.

        Args:
            msg: The log message
            send: If False, log will not be sent over HTTP (default: True)
            **kwargs: Additional metadata to include in the log
        """
        self._logger.info(msg, _send=send, **kwargs)

    def warning(self, msg: str, send: bool = True, **kwargs):
        """
        Log a warning message.

        Args:
            msg: The log message
            send: If False, log will not be sent over HTTP (default: True)
            **kwargs: Additional metadata to include in the log
        """
        self._logger.warning(msg, _send=send, **kwargs)

    def error(self, msg: str, send: bool = True, **kwargs):
        """
        Log an error message.

        Args:
            msg: The log message
            send: If False, log will not be sent over HTTP (default: True)
            **kwargs: Additional metadata to include in the log
        """
        self._logger.error(msg, _send=send, **kwargs)

    def critical(self, msg: str, send: bool = True, **kwargs):
        """
        Log a critical message.

        Args:
            msg: The log message
            send: If False, log will not be sent over HTTP (default: True)
            **kwargs: Additional metadata to include in the log
        """
        self._logger.critical(msg, _send=send, **kwargs)

    # ---- Structlog compatibility ----

    def bind(self, **kwargs):
        return LogiScoutLogger(self._logger.bind(**kwargs))
