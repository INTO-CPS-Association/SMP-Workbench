import json
import pytest
from pathlib import Path

from src.interfaces.file_reading_strategy import FileReadingStrategy
from src.interfaces.log_parsing_strategy import LogParsingStrategy
from src.interfaces.file_wrapper import FileWrapper
from src.interfaces.state_transition_info import StateTransitionInfo
from classes.standard_state_transition_info import StandardStateTransitionInfo
from classes.json_file_wrapper import JsonFileWrapper
from classes.json_file_reading_strategy import JsonFileReadingStrategy
from classes.json_log_parsing_strategy import JsonLogParsingStrategy
from src.interfaces.log_file import LogFile
from src.interfaces.state import State

# Run this before every test function in this file
@pytest.fixture(scope="module", autouse=True)
def setup() -> FileWrapper:
    test_file = Path(__file__).parent.parent.parent / "files" / "test_files" / "test_file0.json"
    jsonFileReadingStrategy: JsonFileReadingStrategy = JsonFileReadingStrategy()
    fileWrapper: JsonFileWrapper = jsonFileReadingStrategy.readFile(test_file)
    return fileWrapper

# Run this before every test function in this file
@pytest.fixture(scope="module", autouse=True)
def setup_real_json_file() -> FileWrapper:
    test_file = Path(__file__).parent.parent.parent / "files" / "test_files" / "state_2025-12-03.json"
    jsonFileReadingStrategy: JsonFileReadingStrategy = JsonFileReadingStrategy()
    fileWrapper: JsonFileWrapper = jsonFileReadingStrategy.readFile(test_file)
    return fileWrapper

def test_JsonLogParsingStrategy_getStates_method_returns_complete_set(setup):
    shouldBe = {"MixingTime", "Dosing", "MixingEmptying", "Idle"}
    result: set = set()

    jsonLogParsingStrategy: LogParsingStrategy = JsonLogParsingStrategy()
    logFile: LogFile = jsonLogParsingStrategy.createLogFile(setup)
    stateTransitionInfoList: list[StateTransitionInfo] = logFile.getStateTransitionInfoList()

    # add the states to result
    for stateTransitionIinfo in stateTransitionInfoList:
        fromState: State = stateTransitionIinfo.getFromState()
        fromStateName: str = fromState.getName()
        toState: State = stateTransitionIinfo.getToState()
        toStateName: str = toState.getName()

        result.add(fromStateName)
        result.add(toStateName)

    assert shouldBe == result

# The amount of from states should be the same as total amount of states
"""
def test_JsonLogParsingStrategy_computePDF_counts_from_states_correctly(setup_real_json_file):

    jsonLogParsingStrategy: JsonLogParsingStrategy = JsonLogParsingStrategy()
    tmp: set = jsonLogParsingStrategy.computeStates(setup_real_json_file)
    shouldBe: int = len(tmp)

    result: list[StandardStateTransitionInfo] = jsonLogParsingStrategy.computePDF(setup_real_json_file)
    result: int = len(result)

    assert shouldBe == result

def test_JsonLogParsingStrategy_computeTransitionCount_each_state_transition_has_at_least_count_1(setup_real_json_file):
    jsonLogParsingStrategy: JsonLogParsingStrategy = JsonLogParsingStrategy()

    stateTransitionInfoList: list[StandardStateTransitionInfo] = jsonLogParsingStrategy.computeStateTransitionCount(setup_real_json_file)

    for instance in stateTransitionInfoList:
        toStates = instance.getToStates()
        
        for transition in toStates:
            assert 1 <= toStates[transition]


def test_JsonLogParsingStrategy_computePDF_for_each_StateTransitionInfo_sum_of_toStates_is_approx_1(setup_real_json_file):
    jsonLogParsingStrategy: JsonLogParsingStrategy = JsonLogParsingStrategy()

    stateTransitionInfoList: list[StandardStateTransitionInfo] = jsonLogParsingStrategy.computePDF(setup_real_json_file)

    for instance in stateTransitionInfoList:
        toStates = instance.getToStates()

        PDFSum: float = 0.0
        for transition in toStates:
            PDFSum += toStates[transition]

        assert abs(PDFSum - 1.0) < 0 + 0.1e-5
"""