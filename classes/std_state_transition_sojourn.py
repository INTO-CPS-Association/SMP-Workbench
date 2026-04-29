from src.interfaces.state_transition_sojourn import StateTransitionSojourn
from classes.standard_state import StandardState
from utils.enums import Distribution
from src.interfaces.state import State

class StdStateTransitionSojourn(StateTransitionSojourn):
    def __init__(self, fromState: StandardState, toState: StandardState, sojournTimes: list[int], sojournAverage: float, sojournMedian: float, distribution: Distribution) -> None:
        self.fromState: State = fromState
        self.toState: State = toState
        self.sojournTimes: list[int] = sojournTimes
        self.sojournAverage: float = sojournAverage
        self.sojournMedian: float = sojournMedian
        self.distribution: Distribution = distribution
    
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
    