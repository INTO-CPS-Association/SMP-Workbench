from src.interfaces.state_transition_probability import StateTransitionProbability
from src.classes.standard_state import StandardState

class StdStateTransitionProbability(StateTransitionProbability):
    def __init__(self, fromState: StandardState, toState: StandardState, probability: float) -> None:
        self.fromState: StandardState = fromState
        self.toState: StandardState = toState
        self.probability: float = probability
    
    def getFromState(self) -> StandardState:
        return self.fromState

    def getToState(self) -> StandardState:
        return self.toState
    
    def getProbability(self) -> float:
        return self.probability