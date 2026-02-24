from src.interfaces.state_transition_info import StateTransitionInfo
from src.interfaces.state import State

class StandardStateTransitionInfo(StateTransitionInfo):
    def __init__(self, fromState: State, toState: State, sojournTime: int):
        self.fromState: State = fromState
        self.toStates: State = toState
        self.sojournTime: int = sojournTime

    def getFromState(self) -> str:
        return self.fromState
    
    def getToState(self) -> dict[str, int]:
        return self.toState
    
    def getSojournTime(self) -> int:
        return self.sojournTime