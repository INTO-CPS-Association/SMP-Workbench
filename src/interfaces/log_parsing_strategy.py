from abc import ABC, abstractmethod
from typing import Any
from src.interfaces.file_wrapper import FileWrapper
from src.interfaces.log_file import LogFile

class LogParsingStrategy(ABC):
    @abstractmethod
    def __init__(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def createLogFile(self, fileWrapper: FileWrapper) -> LogFile:
        raise NotImplementedError