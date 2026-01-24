def remove_internal_fields(logger, method_name, event_dict):
    event_dict.pop("_log_event", None)
    return event_dict
