from abc import ABC, abstractmethod
from interfaces.file_wrapper import FileWrapper
import pathlib

class FileReadingStrategy(ABC):
    @abstractmethod
    def readFile(self, path: pathlib.Path) -> FileWrapper:
        raise NotImplementedError