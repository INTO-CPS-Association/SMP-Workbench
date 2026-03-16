from src.interfaces.state_transition_sojourn import StateTransitionSojourn
from src.classes.standard_state import StandardState

class StdStateTransitionProbability(StateTransitionSojourn):
    def __init__(self, fromState: StandardState, toState: StandardState, sojournTime: int) -> None:
        self.fromState: StandardState = fromState
        self.toState: StandardState = toState
        self.sojournTime: int = sojournTime
    
    def getFromState(self) -> StandardState:
        return self.fromState

    def getToState(self) -> StandardState:
        return self.toState
    
    def getSojournTime(self) -> int:
        return self.sojournTime