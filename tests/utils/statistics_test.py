import pytest
from pathlib import Path
from src.utils.statistics import calculatePDF, calculateSojourn
from src.interfaces.state_transition_info import StateTransitionInfo
from src.interfaces.state_transition_probability import StateTransitionProbability
from src.interfaces.state import State
from src.classes.json_file_wrapper import JsonFileWrapper
from src.classes.json_file_reading_strategy import JsonFileReadingStrategy
from src.classes.json_log_parsing_strategy import JsonLogParsingStrategy
from src.interfaces.log_file import LogFile
from src.interfaces.state_transition_sojourn import StateTransitionSojourn

PRECISION = 0.1e-5

# Run this before every test function in this file
@pytest.fixture(scope="module", autouse=True)
def setup_real_json_file() -> list[StateTransitionInfo]:
    test_file: Path = Path(__file__).parent.parent.parent / "files" / "test_files" / "state_2025-12-03.json"
    jsonFileReadingStrategy: JsonFileReadingStrategy = JsonFileReadingStrategy()
    jsonLogParsingStrategy: JsonLogParsingStrategy = JsonLogParsingStrategy()
    fileWrapper: JsonFileWrapper = jsonFileReadingStrategy.readFile(test_file)
    logFile: LogFile = jsonLogParsingStrategy.createLogFile(fileWrapper)
    stateTransitionInfoList: list[StateTransitionInfo] = logFile.getStateTransitionInfoList()
    return stateTransitionInfoList

def test_calculatePDF_has_sum_of_approximately_1(setup_real_json_file: list[StateTransitionInfo]) -> None:
    tmp: list[StateTransitionInfo] = setup_real_json_file
    stateTransitionProbabilityList: list[StateTransitionProbability] = calculatePDF(tmp)

    # Collect all from states
    fromStateList: list[State] = []
    for stateTransitionProbability in stateTransitionProbabilityList:
        fromStateList.append(stateTransitionProbability.getFromState())

    # Convert state list to a set (for unique values)
    fromStateSet: set[State] = set(fromStateList)

    # Loop trough list of StateTransitionProbability and sum the probability if the from state matches
    for state in fromStateSet:
        PDFSum: float = 0.0

        for stateTransitionProbability in stateTransitionProbabilityList:
            if state == stateTransitionProbability.getFromState():
                PDFSum += stateTransitionProbability.getProbability()
   
        assert abs(PDFSum - 1.0) < 0 + PRECISION

    
def test_calculateSojourn_returns_non_empty_list(setup_real_json_file: list[StateTransitionInfo]) -> None:
    tmp: list[StateTransitionInfo] = setup_real_json_file
    stateTransitionSojournList: list[StateTransitionSojourn] = calculateSojourn(tmp)

    # Collect all from states
    fromStateList: list[State] = []
    for stateTransitionProbability in stateTransitionProbabilityList:
        fromStateList.append(stateTransitionProbability.getFromState())

    # Convert state list to a set (for unique values)
    fromStateSet: set[State] = set(fromStateList)

    # Loop trough list of StateTransitionProbability and sum the probability if the from state matches
    for state in fromStateSet:
        PDFSum: float = 0.0

        for stateTransitionProbability in stateTransitionProbabilityList:
            if state == stateTransitionProbability.getFromState():
                PDFSum += stateTransitionProbability.getProbability()
   
        assert abs(PDFSum - 1.0) < 0 + PRECISION