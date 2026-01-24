import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logiscout_logger import init, get_logger

# Initialize the logger (optional - will auto-configure if not called)

# Get a logger instance
logger = get_logger("http_transport_test")

# Test basic logging - these will be sent to both console and HTTP server
print("\n=== Testing HTTP Transport ===\n")

logger.info("This is an info message", user_id=123, action="login")
logger.warning("This is a warning message", component="auth")
logger.error("This is an error message", error_code="E001")

print("\n=== Test Complete ===")
print("Check your server at http://localhost:3000/logs to verify logs were received.")
