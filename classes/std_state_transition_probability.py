from interfaces.state_transition_probability import StateTransitionProbability
from interfaces.state import State

class StdStateTransitionProbability(StateTransitionProbability):
    def __init__(self, fromState: State, toState: State, probability: float) -> None:
        self.fromState: State = fromState
        self.toState: State = toState
        self.probability: float = probability
    
    def getFromState(self) -> State:
        return self.fromState

    def getToState(self) -> State:
        return self.toState
    
    def getProbability(self) -> float:
        return self.probability