from src.interfaces.state_transition_sojourn import StateTransitionSojourn
from src.classes.standard_state import StandardState

class StdStateTransitionSojourn(StateTransitionSojourn):
    def __init__(self, fromState: StandardState, toState: StandardState, sojournTimes: list[int], sojournAvg: float, sojournMedian: int, distribution: ) -> None:
        self.fromState: StandardState = fromState
        self.toState: StandardState = toState
        self.sojournTimes: list[int] = sojournTimes
        self.sojornAverage: float = 
    
    def getFromState(self) -> StandardState:
        return self.fromState

    def getToState(self) -> StandardState:
        return self.toState
    
    def getSojournTime(self) -> int:
        return self.sojournTime