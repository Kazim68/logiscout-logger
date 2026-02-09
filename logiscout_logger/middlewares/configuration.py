import time
import structlog
from .correlation import asgi_handle_correlation_id, wsgi_handle_correlation_id
from .access import bind_access_context, log_access_entry
from ..buffer import initialize_buffer, start_buffer, set_access_log_data, flush_buffer
from ..logger import get_batch_transport_processor, get_batch_manager

def clear_context():
    """Clear all context variables after request completion"""
    structlog.contextvars.clear_contextvars()

class asgiConfiguration:
    """
    Combined ASGI Middleware that controls the flow for:
    1. Correlation ID management
    2. Access logging and context binding
    """
    def __init__(self, app):
        self.app = app
        self.logger = structlog.get_logger("access_logger")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 1. Handle Correlation ID
        # This binds the correlation_id to contextvars
        correlation_id = asgi_handle_correlation_id(scope)

        # 2. Initialize buffer for this request
        initialize_buffer(correlation_id)

        # 3. Extract Request Info
        method = scope.get("method")
        path = scope.get("path")

        # 4. Set initial access log data in buffer (without status/duration)
        set_access_log_data(method, path)

        # 5. Bind Access Context (for console output)
        # This binds http_method and url_path to contextvars
        bind_access_context(method, path)

        # 6. Start the buffer (ready to accept logs)
        start_buffer()

        # 7. Prepare for Status Capture
        status_code = 200

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        # 8. Execute Request & Measure Time
        start_time = time.time()
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            status_code = 500
            raise       # so that we don't swallow exceptions
        finally:
            process_time_ms = (time.time() - start_time) * 1000

            # 9. Update access log data with final status and duration
            set_access_log_data(method, path, status_code, process_time_ms)

            # 10. Log Access Entry (for console output)
            #log_access_entry(self.logger, method, path, status_code, process_time_ms)

            # 11. Flush buffer and send via batch manager (intelligent batching)
            payload = flush_buffer()
            if payload:
                batch_manager = get_batch_manager()
                if batch_manager:
                    # Use intelligent batch manager (200 logs or 30 seconds)
                    batch_manager.add_payload(payload)
                else:
                    # Fallback to legacy processor if batch manager not available
                    batch_processor = get_batch_transport_processor()
                    if batch_processor:
                        batch_processor.send_payload(payload)

            # 12. Clear context vars for next request
            clear_context()


class wsgiConfiguration:
    """
    Combined WSGI Middleware that controls the flow for:
    1. Correlation ID management
    2. Access logging and context binding
    """
    def __init__(self, app):
        self.app = app
        self.logger = structlog.get_logger("access_logger")

    def __call__(self, environ, start_response):
        # 1. Handle Correlation ID
        correlation_id = wsgi_handle_correlation_id(environ)

        # 2. Initialize buffer for this request
        initialize_buffer(correlation_id)

        # 3. Extract Request Info
        method = environ.get("REQUEST_METHOD")
        path = environ.get("PATH_INFO")

        # 4. Set initial access log data in buffer (without status/duration)
        set_access_log_data(method, path)

        # 5. Bind Access Context early (for console output)
        bind_access_context(method, path)

        # 6. Start the buffer (ready to accept logs)
        start_buffer()

        # 7. Execute Request & Measure Time
        start_time = time.time()
        status_code = [200]
        response_started = [False]

        def start_response_wrapper(status, response_headers, exc_info=None):
            response_started[0] = True
            try:
                status_code[0] = int(status.split(' ')[0])
            except (ValueError, IndexError):
                status_code[0] = 0
            return start_response(status, response_headers, exc_info)

        try:
            # Execute the app completely before yielding
            iterable = self.app(environ, start_response_wrapper)

            # Immediately consume the iterable and collect all data
            # This ensures logs are captured before the next request starts
            response_data = []
            try:
                for data in iterable:
                    response_data.append(data)
            finally:
                # Close the iterable if it has a close method
                if hasattr(iterable, 'close'):
                    iterable.close()

            # Calculate final metrics
            process_time_ms = (time.time() - start_time) * 1000

            # Update access log data with final status and duration
            set_access_log_data(method, path, status_code[0], process_time_ms)

            # Log access entry (for console output)
            #log_access_entry(self.logger, method, path, status_code[0], process_time_ms)

            # Flush buffer and send via batch manager (intelligent batching)
            payload = flush_buffer()
            if payload:
                batch_manager = get_batch_manager()
                if batch_manager:
                    # Use intelligent batch manager (200 logs or 30 seconds)
                    batch_manager.add_payload(payload)
                else:
                    # Fallback to legacy processor if batch manager not available
                    batch_processor = get_batch_transport_processor()
                    if batch_processor:
                        batch_processor.send_payload(payload)

            # Clear context vars for next request
            clear_context()

            # Now yield the response data
            return iter(response_data)

        except Exception:
            status_code[0] = 500

            # Calculate metrics for error case
            process_time_ms = (time.time() - start_time) * 1000

            # Update access log data
            set_access_log_data(method, path, status_code[0], process_time_ms)

            # Log the error case immediately (for console output)
            #log_access_entry(self.logger, method, path, status_code[0], process_time_ms)

            # Flush buffer and send via batch manager (intelligent batching)
            payload = flush_buffer()
            if payload:
                batch_manager = get_batch_manager()
                if batch_manager:
                    # Use intelligent batch manager (200 logs or 30 seconds)
                    batch_manager.add_payload(payload)
                else:
                    # Fallback to legacy processor if batch manager not available
                    batch_processor = get_batch_transport_processor()
                    if batch_processor:
                        batch_processor.send_payload(payload)

            # Clear context vars even on error
            clear_context()
            raise
