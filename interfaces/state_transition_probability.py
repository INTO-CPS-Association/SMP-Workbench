from abc import ABC, abstractmethod
from interfaces.state import State

class StateTransitionProbability(ABC):
    @abstractmethod
    def __init__(self, fromState: State, toState: State, probability: float) -> None:
        raise NotImplementedError
    
    @abstractmethod
    def getFromState(self) -> State:
        raise NotImplementedError
    
    @abstractmethod
    def getToState(self) -> State:
        raise NotImplementedError
    
    @abstractmethod
    def getProbability(self) -> float:
        raise NotImplementedError