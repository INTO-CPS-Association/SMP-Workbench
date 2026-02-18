import json
import pytest
from pathlib import Path
from src.interfaces.file_reading_strategy import FileReadingStrategy
from src.classes.json_file_reading_strategy import JsonFileReadingStrategy

# Run this before every test function in this file
@pytest.fixture(scope="module", autouse=True)
def setup() -> dict:
    test_file = Path(__file__).parent.parent.parent / "files" / "test_files" / "test_file0.json"
    fileStrategy: FileReadingStrategy = JsonFileReadingStrategy()
    tmp = fileStrategy.read(test_file)
    return tmp

def test_LogParserStrategy_getStates_method_returns_set_of_states(setup):
    states = set()

    

    # Iterate through jsonObjects in the logfile and add the possible states to the set
    #for jsonObj in setup:
    #    states.add(jsonObj.get("to_state"))
    #    states.add(jsonObj.get("from_state"))

    shouldBe = {"MixingTime", "Dosing", "MixingEmptying", "Idle"}
    assert shouldBe == states
