import pytest
from pathlib import Path
from src.utils.statistics import calculatePDF

from src.interfaces.file_reading_strategy import FileReadingStrategy
from src.interfaces.log_parsing_strategy import LogParsingStrategy
from src.interfaces.file_wrapper import FileWrapper
from src.interfaces.state_transition_info import StateTransitionInfo
from src.classes.standard_state_transition_info import StandardStateTransitionInfo
from src.classes.json_file_wrapper import JsonFileWrapper
from src.classes.json_file_reading_strategy import JsonFileReadingStrategy
from src.classes.json_log_parsing_strategy import JsonLogParsingStrategy
from src.classes.standard_log_file import StandardLogFile
from src.classes.standard_state import StandardState
from src.classes.std_state_transition_probability import StdStateTransitionProbability

# Run this before every test function in this file
@pytest.fixture(scope="module", autouse=True)
def setup_real_json_file() -> FileWrapper:
    test_file = Path(__file__).parent.parent.parent / "files" / "test_files" / "state_2025-12-03.json"
    jsonFileReadingStrategy: JsonFileReadingStrategy = JsonFileReadingStrategy()
    jsonLogParsingStrategy: JsonLogParsingStrategy = JsonLogParsingStrategy()
    fileWrapper: JsonFileWrapper = jsonFileReadingStrategy.readFile(test_file)
    logFile: StandardLogFile = jsonLogParsingStrategy.createLogFile(fileWrapper)
    stateTransitionInfoList: list[StandardStateTransitionInfo] = logFile.getStateTransitionInfoList()
    return stateTransitionInfoList

def test_calculatePDF_has_sum_of_approximately_1(setup_real_json_file):
    # Sum approx 1
    shouldBe: float = 1.0
    PDFSum: float = 0.0

    tmp: list[StandardStateTransitionInfo] = setup_real_json_file
    stateTransitionProbabilityList: list[StdStateTransitionProbability] = calculatePDF(tmp)
    for stateTransitionProbability in stateTransitionProbabilityList:
        PDFSum += stateTransitionProbability.getProbability()

    print("Len of trans probs:", len(stateTransitionProbabilityList))
    print("PDFSum:", PDFSum)
    assert abs(PDFSum - 1.0) < 0 + 0.1e-5