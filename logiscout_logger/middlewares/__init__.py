"""
LogiScout Middleware Package

This package provides middleware implementations for various web frameworks
to automatically handle correlation IDs and request metadata.
"""

from .configuration import asgiConfiguration, wsgiConfiguration

__all__ = ["asgiConfiguration", "wsgiConfiguration"]

