import json
from src.interfaces.log_file import LogFile

class JsonLogFile(LogFile):

    def get(self) -> list[dict]:
        return self.file
    
    def set(self, jsonObj: list[dict]) -> None:
        self.file = jsonObj