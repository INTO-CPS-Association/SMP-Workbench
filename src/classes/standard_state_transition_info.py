from src.interfaces.state_transition_info import StateTransitionInfo

class StandardStateTransitionInfo(StateTransitionInfo):
    def __init__(self, from_state: str):
        self.fromState: str = from_state
        self.toStates: dict[str, int] = {}

    def getFromState(self) -> str:
        return self.fromState
    
    def getToStates(self) -> dict[str, int]:
        return self.toStates
    
    def setToStates(self, toStates: dict[str, int]) -> None:
        self.toStates: dict[str, int] = toStates