from .transports import ConsoleTransport
from .transports.http import HTTPTransport
from .processors import build_log_event, remove_internal_fields, filter_info_and_above, TransportProcessor
import structlog
import threading
import logging

# ------------------------
# Global configuration
# ------------------------

_config = {
    "endpoint": None,
    "service_name": None,
}

_configured = False
_lock = threading.Lock()


# ------------------------
# Public init()
# ------------------------

def init(
    *,
    endpoint: str,
    service_name: str,
):
    """
    Initialize LogiScout logger.
    Must be called once at app startup.
    """
    global _configured

    with _lock:
        if _configured:
            return

        _config["endpoint"] = endpoint
        _config["service_name"] = service_name

        _configure_structlog()

        _configured = True

# ------------------------
# Structlog configuration
# ------------------------

def _configure_structlog():
    """
    Configure structlog for console output.
    """

    logging.basicConfig(level=logging.DEBUG)     # this shows logs with log levels of INFO or above

    # Build processor list
    processors = [
        # filter_info_and_above,
        structlog.processors.TimeStamper(fmt="iso"),
        # structlog.stdlib.add_logger_name,
        # structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,

        # --- remote pipeline ---
        build_log_event,
    ]

    # Add HTTP transport only if endpoint is configured
    if _config["endpoint"]:
        http_transport = HTTPTransport(_config["endpoint"])
        processors.append(TransportProcessor(http_transport))

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
    Returns a LogoScout logger instance.
    """
    if not _configured:
        # Safe fallback
        _configure_structlog()

    base_logger = structlog.get_logger(name)
    return LogiScoutLogger(base_logger)


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

    def debug(self, msg: str, **kwargs):
        self._logger.debug(msg, **kwargs)

    def info(self, msg: str, **kwargs):
        self._logger.info(msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        self._logger.warning(msg, **kwargs)

    def error(self, msg: str, **kwargs):
        self._logger.error(msg, **kwargs)

    def critical(self, msg: str, **kwargs):
        self._logger.critical(msg, **kwargs)

    # ---- Structlog compatibility ----

    def bind(self, **kwargs):
        return LogiScoutLogger(self._logger.bind(**kwargs))
