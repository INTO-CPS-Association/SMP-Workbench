import json
import pathlib
from src.interfaces.file_reading_strategy import FileReadingStrategy
from src.interfaces.file_wrapper import FileWrapper
from src.classes.json_file_wrapper import JsonFileWrapper

class JsonFileReadingStrategy(FileReadingStrategy):

    # Arg1: Path to file
    # Returns: List of json objects
    def readFile(self, path: str) -> JsonFileWrapper:
        results = []
        file_extension: str = pathlib.Path(path).suffix
        if ".json" in file_extension:
            with open(path, 'r') as file:
                start_pos: int = file.tell()
                tmp: str = file.readline()

                if "The logger is now ready" in tmp:
                    # Do nothing - first line skipped successfully (cannot be parsed as json)
                    pass
                else:
                    file.seek(start_pos)
                
                # Logic for iterating through json objects
                for line in file:
                    line.strip() # Remove newlines
                    if line:
                        results.append(json.loads(line)) # If line has something in it - append it to results as a json object

            return JsonFileWrapper(results)
        else:
            raise(OSError("File did not end with .json"))