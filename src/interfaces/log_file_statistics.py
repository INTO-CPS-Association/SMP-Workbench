from abc import ABC, abstractmethod
from interfaces.state_transition_probability import StateTransitionProbability

class LogFileStatistics(ABC):
    @abstractmethod
    def __init__(self, stateTransitionProbabilityList: list[StateTransitionProbability]) -> None:
        raise NotImplementedError
    
    @abstractmethod
    def getStateTransitionProbabilityList() -> list[StateTransitionProbability]:
        raise NotImplementedError
    
    @abstractmethod
    def getSojourn():
        raise NotImplementedError