from interfaces.state_transition_statistics import StateTransitionStatistics
from utils.enums import Distribution
from interfaces.state import State

class StdStateTransitionStatistics(StateTransitionStatistics):
    def __init__(self, fromState: State, toState: State, sojournTimes: list[int], sojournAverage: float, sojournMedian: float, distribution: Distribution, probability: float) -> None:
        self.fromState: State = fromState
        self.toState: State = toState
        self.sojournTimes: list[int] = sojournTimes
        self.sojournAverage: float = sojournAverage
        self.sojournMedian: float = sojournMedian
        self.distribution: Distribution = distribution
        self.probability: float = probability
    
    def getFromState(self) -> State:
        return self.fromState

    def getToState(self) -> State:
        return self.toState
    
    def getSojournTimes(self) -> list[int]:
        return self.sojournTimes
    
    def getSojournAverage(self) -> float:
        return self.sojournAverage
    
    def getSojournMedian(self) -> float:
        return self.sojournMedian
    
    def getDistribution(self) -> Distribution:
        return self.distribution
    
    def getProbability(self) -> float:
        return self.probability
    