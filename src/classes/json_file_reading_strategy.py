import json
from src.interfaces.file_reading_strategy import FileReadingStrategy

class JsonFileReadingStrategy(FileReadingStrategy):

    # Arg1: Path to file
    # Returns: List of json objects
    def read(self, path: str) -> list[str]:
        results = []
        with open(path, 'r') as file:
            for line in file:
                line.strip() # Remove newlines
                if line:
                    results.append(json.loads(line)) # If line has something in it - append it to results as a json object

        return results