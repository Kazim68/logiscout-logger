from pprint import pprint
from .base import Transport
from ..events import LogEvent


class ConsoleTransport(Transport):
    """
    Development transport.
    Prints LogEvent to console.
    """

    def send(self, event: LogEvent) -> None:
        print("\n--- LogEvent (remote pipeline) ---")
        pprint(event)
        print("--- End LogEvent ---\n")
