from .logger import get_logger, init, Environment, DEV, PROD
from .middlewares import asgiConfiguration, wsgiConfiguration

__all__ = [
    "get_logger",
    "init",
    "Environment",
    "DEV",
    "PROD",
    "asgiConfiguration",
    "wsgiConfiguration",
]

__version__ = "0.2.0"
__description__ = "LogiScout Logger Library with advanced correlation ID middleware support"
__author__ = "LogiScout Team"