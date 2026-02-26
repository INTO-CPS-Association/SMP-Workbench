import json
from src.interfaces.file_wrapper import FileWrapper

class JsonFileWrapper(FileWrapper):
    def __init__(self, objectList: list[dict]):
        self.objectList = objectList
    def getObjectList(self) -> list[dict]:
        return self.objectList