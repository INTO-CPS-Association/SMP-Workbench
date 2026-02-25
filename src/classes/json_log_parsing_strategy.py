import json
from src.interfaces.log_parsing_strategy import LogParsingStrategy
from src.classes.json_file_wrapper import JsonFileWrapper
from src.interfaces.log_file import LogFile
from src.classes.json_file_wrapper import JsonFileWrapper
from src.classes.standard_state_transition_info import StandardStateTransitionInfo
from src.classes.standard_state import StandardState
from src.classes.standard_log_file import StandardLogFile

class JsonLogParsingStrategy(LogParsingStrategy):
    def __init__(self) -> None:
        pass
        
    def createLogFile(self, fileWrapper: JsonFileWrapper) -> LogFile:
        # Initialize empty list, will be used to initialize StandardLogFIle 
        stateTansitionInfoList: list[StandardStateTransitionInfo] = []

        # Iterate through the list of json objects from the fileWrapper
        jsonObjects: list[dict] = fileWrapper.getObjectList()
        for jsonObject in jsonObjects:
            # Create state objects
            fromState: StandardState = StandardState(jsonObject["from_state"])
            toState: StandardState = StandardState(jsonObject["to_state"])
            sojournTime: int = jsonObject["sojourn_sec"]
            stateTransitionInfo: StandardStateTransitionInfo = StandardStateTransitionInfo(fromState, toState, sojournTime)
            stateTansitionInfoList.append(stateTransitionInfo)
        
        return StandardLogFile(stateTansitionInfoList)