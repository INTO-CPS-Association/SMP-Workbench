from src.interfaces.log_file import LogFile
from src.interfaces.state_transition_info import StateTransitionInfo

class StandardLogFile(LogFile):
       # Force giving parameters during creation
    def __init__(self, stateTransitionInfoList: list[StateTransitionInfo]) -> None:
        self.stateTransitionInfoList = stateTransitionInfoList

    def getStateTransitionInfoList(self) -> list[StateTransitionInfo]:
        return self.stateTransitionInfoList