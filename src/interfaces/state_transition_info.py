from abc import ABC, abstractmethod
from src.interfaces.state import State

class StateTransitionInfo(ABC):

    @abstractmethod
    def __init__(self, fromState: State, toState: State, sojournTime: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def getFromState(self) -> str:
        raise NotImplementedError
    
    @abstractmethod
    def getToState(self) -> dict[str, int]:
        raise NotImplementedError
    
    @abstractmethod
    def getSojournTime(self) -> int:
        raise NotImplementedError