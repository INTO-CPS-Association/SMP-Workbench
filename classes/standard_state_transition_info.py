from interfaces.state_transition_info import StateTransitionInfo
from interfaces.state import State

class StandardStateTransitionInfo(StateTransitionInfo):
    def __init__(self, fromState: State, toState: State, sojournTime: int):
        self.fromState: State = fromState
        self.toState: State = toState
        self.sojournTime: int = sojournTime

    def getFromState(self) -> State:
        return self.fromState
    
    def getToState(self) -> State:
        return self.toState
    
    def getSojournTime(self) -> int:
        return self.sojournTime
    
    # If the fromState and toState of the two instances are equal they are describing
    # an occurance of the same transition (they are equal). In all other cases they are not equal.
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StateTransitionInfo):
            return False
        
        if self.fromState == other.getFromState():
            if self.toState == other.getToState():
                return True
            
        return False