import json
import pathlib
from src.interfaces.file_reading_strategy import FileReadingStrategy
from src.interfaces.file_wrapper import FileWrapper
from src.classes.json_file_wrapper import JsonFileWrapper

class JsonFileReadingStrategy(FileReadingStrategy):

    # Arg1: Path to file
    # Returns: List of json objects
    def read(self, path: str) -> JsonFileWrapper:
        results = []
        file_extension: str = pathlib.Path(path).suffix
        print("file extension:", file_extension)
        if ".json" in file_extension:
            with open(path, 'r') as file:
                for line in file:
                    line.strip() # Remove newlines
                    if line:
                        results.append(json.loads(line)) # If line has something in it - append it to results as a json object

            return JsonFileWrapper(results)
        else:
            raise(OSError("File did not end with .json"))