from abc import ABC, abstractmethod

class LogFileStatistics(ABC):
    @abstractmethod
    def __init__(self) -> None:
        raise NotImplementedError