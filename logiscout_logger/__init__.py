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

__version__ = "0.1.0"
__description__ = "LogiScout Logger Library - Structured logging for ingesting logs into LogiScout"
__author__ = "Abdur Rehman Kazim"