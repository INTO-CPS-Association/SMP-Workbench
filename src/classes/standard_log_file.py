from src.interfaces.log_file import LogFile

class StandardLogFile(LogFile):
       # Force giving parameters during creation
    def __init__(self, states: set, PDF: int, sojourn: int):
        self.states: set = states
        self.PDF: int = PDF
        self.sojourn: int = sojourn

    def getStates(self) -> set[str]:
        return self.states
    
    def getPDF(self) -> int:
        raise NotImplementedError

    def getSojournTime(self) -> int:
        raise NotImplementedError