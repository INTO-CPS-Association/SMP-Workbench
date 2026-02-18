import json
from pathlib import Path
from src.interfaces.file_reading_strategy import FileReadingStrategy
from src.classes.json_file_reading_strategy import JsonFileReadingStrategy


def test_FileReadingStrategy_read_method_returns_json_object():
    test_file = Path(__file__).parent.parent.parent / "files" / "test_files" / "test_file0.json"
    fileStrategy: FileReadingStrategy = JsonFileReadingStrategy()
    tmp = fileStrategy.read(test_file)
    result = tmp[0].get("component")
    assert "physical_twin" == result
