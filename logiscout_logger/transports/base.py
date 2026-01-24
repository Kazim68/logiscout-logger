from abc import ABC, abstractmethod
from ..events import LogEvent


class Transport(ABC):
    """
    Base class for all transports.
    """

    @abstractmethod
    def send(self, event: LogEvent) -> None:
        pass
