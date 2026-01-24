from enum import Enum


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

# Level weights/priorities (lower = more verbose)
LEVEL_WEIGHTS = {
    LogLevel.DEBUG: 10,
    LogLevel.INFO: 20,
    LogLevel.WARNING: 30,
    LogLevel.ERROR: 40,
    LogLevel.CRITICAL: 50,
}

# Default minimum level
DEFAULT_MIN_LEVEL = LogLevel.INFO
DEFAULT_MIN_LEVEL_WEIGHT = LEVEL_WEIGHTS[DEFAULT_MIN_LEVEL]