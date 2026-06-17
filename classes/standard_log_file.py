from interfaces.log_file import LogFile
from interfaces.state_transition_info import StateTransitionInfo

class StandardLogFile(LogFile):
       # Force giving parameters during creation
    def __init__(self, stateTransitionInfoList: list[StateTransitionInfo]) -> None:
        self.stateTransitionInfoList: list[StateTransitionInfo] = stateTransitionInfoList

    def getStateTransitionInfoList(self) -> list[StateTransitionInfo]:
        return self.stateTransitionInfoList