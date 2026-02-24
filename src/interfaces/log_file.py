from abc import ABC, abstractmethod
from src.interfaces.state_transition_info import StateTransitionInfo

class LogFile(ABC):
    # Force giving parameters during creation
    @abstractmethod
    def __init__(self, states: set, PDF: int, sojourn: int) -> None:
        raise NotImplementedError
    
    def getStateTransitionInfoList() -> list[StateTransitionInfo]:
        raise NotImplementedError