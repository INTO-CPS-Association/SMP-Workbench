from abc import ABC, abstractmethod
from typing import Any

class LogFile(ABC):
    # Force giving file as constructor parameter
    def __init__(self, file: Any):
        self.file = file

    # Return type specified in subclass - depends on what self.file
    @abstractmethod
    def getSojournTime(self) -> list[int]:
        raise NotImplementedError
    
    # Allow user to change the file at runtime by making a setter method
    @abstractmethod
    def set(self) -> None:
        raise NotImplementedError