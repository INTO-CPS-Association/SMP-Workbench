from abc import ABC, abstractmethod
from interfaces.state import State

class StateTransitionInfo(ABC):

    @abstractmethod
    def __init__(self, fromState: State, toState: State, sojournTime: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def getFromState(self) -> State:
        raise NotImplementedError
    
    @abstractmethod
    def getToState(self) -> State:
        raise NotImplementedError
    
    @abstractmethod
    def getSojournTime(self) -> int:
        raise NotImplementedError
    
    @abstractmethod
    def __eq__(self, other: object)  -> bool:
        raise NotImplementedError