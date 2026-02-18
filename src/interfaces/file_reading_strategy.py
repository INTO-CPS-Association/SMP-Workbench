from abc import ABC, abstractmethod
from src.interfaces.log_file import LogFile

class FileReadingStrategy(ABC):
    @abstractmethod
    def read(self, path: str) -> LogFile:
        raise NotImplementedError