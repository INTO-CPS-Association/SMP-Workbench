import json
from pathlib import Path
from src.interfaces.file_reading_strategy import FileReadingStrategy
from src.classes.json_file_reading_strategy import JsonFileReadingStrategy
from src.classes.json_log_file import JsonLogFile



def test_FileReadingStrategy_read_method_returns_json_object():
    test_file = Path(__file__).parent.parent.parent / "files" / "test_files" / "test_file0.json"
    fileStrategy: FileReadingStrategy = JsonFileReadingStrategy()
    jsonLogFile : JsonLogFile = fileStrategy.read(test_file)
    jsonObj: dict = jsonLogFile.get()
    result: str = jsonObj[0].get("component")

    shouldBe = "physical_twin"
    assert shouldBe == result
