from src.interfaces.file_wrapper import FileWrapper

class JsonFileWrapper(FileWrapper):
    def __init__(self, objectList: list[dict[str, str]]):
        self.objectList = objectList

    def getObjectList(self) -> list[dict[str, str]]:
        return self.objectList