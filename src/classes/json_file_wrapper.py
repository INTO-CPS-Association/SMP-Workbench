import json
from src.interfaces.file_wrapper import FileWrapper

class JsonFileWrapper(FileWrapper):

    def getFile(self) -> list[dict]:
        return self.file
    
    def setFile(self, jsonObj: list[dict]) -> None:
        self.file = jsonObj