from src.interfaces.log_parsing_strategy import LogParsingStrategy
from src.interfaces.file_wrapper import FileWrapper
from src.classes.json_file_wrapper import JsonFileWrapper

class JsonLogParsingStrategy(LogParsingStrategy):
    def computeStates(self, fileWrapper: FileWrapper) -> set:
        result: set = set()
        jsonObjects : FileWrapper = fileWrapper.getFile()
        
        for jsonObject in jsonObjects:
            result.add(jsonObject["to_state"])
            result.add(jsonObject["from_state"])

        return result
    
    def computePDF(self, logFile):
        raise NotImplementedError
    
    def computeSojourn(self, logFile):
        raise NotImplementedError
    
    # TODO: Just a prototype
    def createLogFile(self, fileWrapper):
        #states: set = self.__computeStates(fileWrapper)
        #pdf: int = self.__computePDF(fileWrapper)
        #sojourn: int = self.__computeSojourn(fileWrapper)
        #return StandardLogFile(states, pdf, sojourn)
        raise NotImplementedError
    