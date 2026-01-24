import structlog
from ..levels import LEVEL_WEIGHTS, LogLevel

def create_level_filter(min_level: LogLevel = LogLevel.INFO):
    """
    Create a filter function that only allows logs at or above min_level.
    
    Usage:
        filter_by_level = create_level_filter(LogLevel.INFO)
    """
    min_weight = LEVEL_WEIGHTS[min_level]
    
    def filter_by_level(logger, method_name, event_dict):
        """Filter logs based on level."""
        method_weight = LEVEL_WEIGHTS.get(method_name, 0)
        
        if method_weight < min_weight:
            raise structlog.DropEvent
        return event_dict
    
    return filter_by_level

# Pre-configured filters for convenience
filter_info_and_above = create_level_filter(LogLevel.INFO)
filter_warning_and_above = create_level_filter(LogLevel.WARNING)
filter_error_and_above = create_level_filter(LogLevel.ERROR)