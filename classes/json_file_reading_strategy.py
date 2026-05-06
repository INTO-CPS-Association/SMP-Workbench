import json
import pathlib
from src.interfaces.file_reading_strategy import FileReadingStrategy
from classes.json_file_wrapper import JsonFileWrapper

class JsonFileReadingStrategy(FileReadingStrategy):

    # Arg1: Path to file
    # Returns: List of json objects
    def readFile(self, path: pathlib.Path) -> JsonFileWrapper:
        results: list[dict[str,str]]= []
        file_extension: str = pathlib.Path(path).suffix
        if ".json" in file_extension:
            with open(path, 'r') as file:
                for line in file:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue  # skip non-JSON lines (e.g. "The logger is now ready")

            return JsonFileWrapper(results)
        
        else:
            raise OSError("File did not end with .json")