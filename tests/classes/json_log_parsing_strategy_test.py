import json
import pytest
from pathlib import Path

from src.interfaces.file_reading_strategy import FileReadingStrategy
from src.interfaces.log_parsing_strategy import LogParsingStrategy
from src.classes.json_file_wrapper import JsonFileWrapper
from src.classes.json_file_reading_strategy import JsonFileReadingStrategy
from src.classes.json_log_parsing_strategy import JsonLogParsingStrategy

# Run this before every test function in this file
@pytest.fixture(scope="module", autouse=True)
def setup() -> dict:
    test_file = Path(__file__).parent.parent.parent / "files" / "test_files" / "test_file0.json"
    jsonFileReadingStrategy: JsonFileReadingStrategy = JsonFileReadingStrategy()
    fileWrapper: JsonFileWrapper = jsonFileReadingStrategy.read(test_file)
    return fileWrapper

def test_JsonLogParsingStrategy_getStates_method_return_type_is_set(setup):
    shouldBe = type(set())

    jsonLogParsingStrategy: JsonLogParsingStrategy = JsonLogParsingStrategy()
    result: set = jsonLogParsingStrategy.computeStates(setup)
    result = type(result)
    assert shouldBe == result

def test_JsonLogParsingStrategy_getStates_method_returns_complete_set(setup):
    shouldBe = {"MixingTime", "Dosing", "MixingEmptying", "Idle"}

    result = set()
    jsonLogParsingStrategy: LogParsingStrategy = JsonLogParsingStrategy()
    result: set = jsonLogParsingStrategy.computeStates(setup)
    assert shouldBe == result

