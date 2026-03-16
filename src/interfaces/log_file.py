from abc import ABC, abstractmethod
from src.interfaces.state_transition_info import StateTransitionInfo

class LogFile(ABC):
    # Force giving parameters during creation
    @abstractmethod
    def __init__(self, stateTransitionInfoList: list[StateTransitionInfo]) -> None:
        raise NotImplementedError
    
    def getStateTransitionInfoList(self) -> list[StateTransitionInfo]:
        raise NotImplementedError