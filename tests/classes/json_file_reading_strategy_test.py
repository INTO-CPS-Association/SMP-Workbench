import json
import pytest
from pathlib import Path
from src.interfaces.file_reading_strategy import FileReadingStrategy
from src.classes.json_file_reading_strategy import JsonFileReadingStrategy
from src.classes.json_file_wrapper import JsonFileWrapper

def test_JsonFileReadingStrategy_read_method_returns_json_file_wrapper_class():
    test_file = Path(__file__).parent.parent.parent / "files" / "test_files" / "test_file0.json"
    fileStrategy: FileReadingStrategy = JsonFileReadingStrategy()
    jsonFileWrapper : JsonFileWrapper = fileStrategy.readFile(test_file)
    result: JsonFileWrapper = jsonFileWrapper
    shouldBe = JsonFileWrapper
    assert shouldBe == type(result)

def test_JsonFileReadingStrategy_read_method_throws_OS_exception_on_wrong_file_type():
    test_file = Path(__file__).parent.parent.parent / "files" / "test_files" / "test_exception_file.txt"
    fileStrategy: FileReadingStrategy = JsonFileReadingStrategy()
    with pytest.raises(OSError):
        _ : JsonFileWrapper = fileStrategy.readFile(test_file)

def test_JsonFileReadingStrategy_read_method_throws_OS_exception_with_proper_value_on_wrong_file_type():
    test_file = Path(__file__).parent.parent.parent / "files" / "test_files" / "test_exception_file.txt"
    fileStrategy: FileReadingStrategy = JsonFileReadingStrategy()
    with pytest.raises(OSError) as excinfo:
        _ : JsonFileWrapper = fileStrategy.readFile(test_file)
    
    assert "File did not end with .json" == str(excinfo.value)