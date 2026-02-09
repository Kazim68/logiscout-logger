def remove_internal_fields(logger, method_name, event_dict):
    """
    Remove internal fields before console output.
    Removes fields that are:
    - Internal (_log_event, _send)
    - Already captured at request level (correlation_id, http_method, url_path)
    """
    event_dict.pop("_log_event", None)
    event_dict.pop("_send", None)
    event_dict.pop("correlation_id", None)
    event_dict.pop("http_method", None)
    event_dict.pop("url_path", None)
    return event_dict
