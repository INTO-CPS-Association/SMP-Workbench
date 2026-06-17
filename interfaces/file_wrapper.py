from abc import ABC, abstractmethod
from typing import Any

class FileWrapper(ABC):
    # Force giving file as constructor parameter
    def __init__(self, objectList: Any) -> None:
        raise NotImplementedError
    
    # Return type specified in subclass - depends on what self.file
    @abstractmethod
    def getObjectList(self) -> Any:
        raise NotImplementedError