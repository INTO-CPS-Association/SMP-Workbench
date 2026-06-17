from abc import ABC, abstractmethod
from interfaces.state import State

class StateTransitionStatistics(ABC):
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
    def getSojournTimes(self) -> list[int]:
        raise NotImplementedError

    @abstractmethod
    def getSojournAverage(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def getSojournMedian(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def getProbability(self) -> float:
        raise NotImplementedError