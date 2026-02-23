import json
from src.interfaces.log_parsing_strategy import LogParsingStrategy
from src.interfaces.file_wrapper import FileWrapper
from src.classes.json_file_wrapper import JsonFileWrapper
from src.classes.standard_state_transition_info import StandardStateTransitionInfo

class JsonLogParsingStrategy(LogParsingStrategy):
    def computeStates(self, fileWrapper: FileWrapper) -> set:
        result: set = set()
        jsonObjects : dict = fileWrapper.getFile()
        
        for jsonObject in jsonObjects:
            result.add(jsonObject["to_state"])
            result.add(jsonObject["from_state"])

        return result
    
    def computeStateTransitionCount(self, fileWrapper: FileWrapper) -> list[StandardStateTransitionInfo]:
        stateTransitionList: list[StandardStateTransitionInfo] = []
        jsonObjects : dict = fileWrapper.getFile()

        # Create a list of all states in the log file and initiate an instance for each one
        fromStates: set = self.computeStates(fileWrapper)
        for state in fromStates:
            stateTransitionList.append(StandardStateTransitionInfo(state))

        # Traverse through the StandardStateTransitionsInfo list and find the to_states to create the dict
        for instance in stateTransitionList:
            fromState: str = instance.getFromState()

            # Traverse through the list of jsonObjects and create/count the amount of times a transition happens
            for jsonObject in jsonObjects:
                toStates: dict[str, int] = instance.getToStates()

                # Check if the from_state field matches the name of this instance
                if fromState == jsonObject["from_state"]:
                    key: str = jsonObject["to_state"]

                    # If the key exists, increment its count - else create the key with count 1
                    if key in toStates:
                        toStates[key] = toStates[key] + 1
                    else:
                        toStates[key] = 1
                
                instance.setToStates(toStates)
        
        return stateTransitionList

    
    def computePDF(self, fileWrapper: FileWrapper) -> list[StandardStateTransitionInfo]:
        stateTransitionInfoList: list[StandardStateTransitionInfo] = []

        stateTransitionInfoList = self.computeStateTransitionCount(fileWrapper)

        for instance in stateTransitionInfoList:
            transitionSum: int = 0.0
            toStates: dict[str, int] = instance.getToStates()
            
            # Calculate the count of all transitions
            for key in toStates:
                transitionSum += toStates[key]
            
            # Divide each transition with the tolt
            for key in toStates:
                toStates[key] = toStates[key]/transitionSum

        return stateTransitionInfoList
    
    def computeSojourn(self, logFile):
        raise NotImplementedError
    
    # TODO: Just a prototype
    def createLogFile(self, fileWrapper: FileWrapper):
        #states: set = self.__computeStates(fileWrapper)
        #pdf: int = self.__computePDF(fileWrapper)
        #sojourn: int = self.__computeSojourn(fileWrapper)
        #return StandardLogFile(states, pdf, sojourn)
        raise NotImplementedError
    