import pytest
from pathlib import Path
from utils.statistics import calculateStatistics
from src.interfaces.state_transition_info import StateTransitionInfo
from src.interfaces.state import State
from classes.json_file_wrapper import JsonFileWrapper
from classes.json_file_reading_strategy import JsonFileReadingStrategy
from classes.json_log_parsing_strategy import JsonLogParsingStrategy
from src.interfaces.log_file import LogFile
from src.interfaces.state_transition_statistics import StateTransitionStatistics

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

def test_calculateStatistics_PDF_result_has_sum_of_approximately_1(setup_real_json_file: list[StateTransitionInfo]) -> None:
    tmp: list[StateTransitionInfo] = setup_real_json_file
    result = calculateStatistics(tmp)
    stateTransitionStatisticsList: list[StateTransitionStatistics] = result.statistics

    fromStateSet: set[State] = {s.getFromState() for s in stateTransitionStatisticsList}

    for state in fromStateSet:
        PDFSum: float = 0.0
        for stateTransitionStatistics in stateTransitionStatisticsList:
            if state == stateTransitionStatistics.getFromState():
                PDFSum += stateTransitionStatistics.getProbability()
        assert abs(PDFSum - 1.0) < 0 + PRECISION
