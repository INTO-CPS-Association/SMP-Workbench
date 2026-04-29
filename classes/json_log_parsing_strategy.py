from src.interfaces.log_parsing_strategy import LogParsingStrategy
from src.interfaces.log_file import LogFile
from src.interfaces.file_wrapper import FileWrapper
from classes.standard_state_transition_info import StandardStateTransitionInfo
from classes.standard_state import StandardState
from classes.standard_log_file import StandardLogFile
from src.interfaces.state_transition_info import StateTransitionInfo

class JsonLogParsingStrategy(LogParsingStrategy):
    def __init__(self) -> None:
        pass
        
    def createLogFile(self, fileWrapper: FileWrapper) -> LogFile:
        # Initialize empty list, will be used to initialize StandardLogFIle 
        stateTansitionInfoList: list[StateTransitionInfo] = []

        # Iterate through the list of json objects from the fileWrapper
        jsonObjects: list[dict[str, str]] = fileWrapper.getObjectList()
        for jsonObject in jsonObjects:
            # Create state objects
            fromState: StandardState = StandardState(jsonObject["from_state"])
            toState: StandardState = StandardState(jsonObject["to_state"])
            sojournTime: int = int(jsonObject["sojourn_sec"])
            stateTransitionInfo: StandardStateTransitionInfo = StandardStateTransitionInfo(fromState, toState, sojournTime)
            stateTansitionInfoList.append(stateTransitionInfo)
        
        return StandardLogFile(stateTansitionInfoList)