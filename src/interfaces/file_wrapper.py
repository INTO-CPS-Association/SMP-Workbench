from abc import ABC, abstractmethod
from typing import Any

class FileWrapper(ABC):
    # Force giving file as constructor parameter
    def __init__(self, file: Any):
        self.file = file

    # Return type specified in subclass - depends on what self.file
    @abstractmethod
    def getFile(self) -> Any:
        raise NotImplementedError
    
    # Allow user to change the file at runtime by making a setter method
    @abstractmethod
    def setFile(self) -> None:
        raise NotImplementedError