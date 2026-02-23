from abc import ABC, abstractmethod
from typing import Any

class LogFile(ABC):
    # Force giving parameters during creation
    @abstractmethod
    def __init__(self, states: set, PDF: int, sojourn: int):
        self.states: set = states
        self.PDF: int = PDF
        self.sojourn: int = sojourn

    @abstractmethod
    def getStates(self) -> set[str]:
        raise NotImplementedError
    
    @abstractmethod
    def getPDF(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def getSojournTime(self) -> dict:
        raise NotImplementedError