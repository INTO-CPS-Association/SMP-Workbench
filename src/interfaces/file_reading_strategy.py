from abc import ABC, abstractmethod
from src.interfaces.file_wrapper import FileWrapper

class FileReadingStrategy(ABC):
    @abstractmethod
    def readFile(self, path: str) -> FileWrapper:
        raise NotImplementedError