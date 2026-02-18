import json
from src.interfaces.file_reading_strategy import FileReadingStrategy
from src.interfaces.log_file import LogFile
from src.classes.json_log_file import JsonLogFile

class JsonFileReadingStrategy(FileReadingStrategy):

    # Arg1: Path to file
    # Returns: List of json objects
    def read(self, path: str) -> LogFile:
        results = []
        with open(path, 'r') as file:
            for line in file:
                line.strip() # Remove newlines
                if line:
                    results.append(json.loads(line)) # If line has something in it - append it to results as a json object

        return JsonLogFile(results)