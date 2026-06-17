from interfaces.log_parsing_strategy import LogParsingStrategy
from interfaces.log_file import LogFile
from interfaces.state_transition_info import StateTransitionInfo
from classes.json_file_wrapper import JsonFileWrapper
from classes.json_file_reading_strategy import JsonFileReadingStrategy
from classes.json_log_parsing_strategy import JsonLogParsingStrategy
from classes.standard_state import StandardState
from classes.standard_state_transition_info import StandardStateTransitionInfo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wrapper(records: list[dict]) -> JsonFileWrapper:
    return JsonFileWrapper(records)


# ---------------------------------------------------------------------------
# Type contract
# ---------------------------------------------------------------------------

class TestJsonLogParsingStrategyType:
    def test_is_log_parsing_strategy(self):
        assert isinstance(JsonLogParsingStrategy(), LogParsingStrategy)

    def test_create_log_file_returns_log_file(self, tmp_json_file):
        reader = JsonFileReadingStrategy()
        parser = JsonLogParsingStrategy()
        log = parser.createLogFile(reader.readFile(tmp_json_file))
        assert isinstance(log, LogFile)

    def test_transitions_are_state_transition_info_instances(self, tmp_json_file):
        reader = JsonFileReadingStrategy()
        parser = JsonLogParsingStrategy()
        for t in parser.createLogFile(reader.readFile(tmp_json_file)).getStateTransitionInfoList():
            assert isinstance(t, StateTransitionInfo)


# ---------------------------------------------------------------------------
# Parsing accuracy
# ---------------------------------------------------------------------------

class TestJsonLogParsingStrategyParsing:
    def test_correct_number_of_transitions(self, tmp_json_file):
        reader = JsonFileReadingStrategy()
        parser = JsonLogParsingStrategy()
        transitions = parser.createLogFile(reader.readFile(tmp_json_file)).getStateTransitionInfoList()
        assert len(transitions) == 4

    def test_from_state_name_correct(self):
        wrapper = _make_wrapper([{"from_state": "Idle", "to_state": "Dosing", "sojourn_sec": 30}])
        t = JsonLogParsingStrategy().createLogFile(wrapper).getStateTransitionInfoList()[0]
        assert t.getFromState().getName() == "Idle"

    def test_to_state_name_correct(self):
        wrapper = _make_wrapper([{"from_state": "Idle", "to_state": "Dosing", "sojourn_sec": 30}])
        t = JsonLogParsingStrategy().createLogFile(wrapper).getStateTransitionInfoList()[0]
        assert t.getToState().getName() == "Dosing"

    def test_sojourn_time_correct(self):
        wrapper = _make_wrapper([{"from_state": "A", "to_state": "B", "sojourn_sec": 42}])
        t = JsonLogParsingStrategy().createLogFile(wrapper).getStateTransitionInfoList()[0]
        assert t.getSojournTime() == 42

    def test_sojourn_time_is_int(self):
        wrapper = _make_wrapper([{"from_state": "A", "to_state": "B", "sojourn_sec": 7}])
        t = JsonLogParsingStrategy().createLogFile(wrapper).getStateTransitionInfoList()[0]
        assert isinstance(t.getSojournTime(), int)

    def test_state_objects_are_standard_state(self):
        wrapper = _make_wrapper([{"from_state": "X", "to_state": "Y", "sojourn_sec": 1}])
        t = JsonLogParsingStrategy().createLogFile(wrapper).getStateTransitionInfoList()[0]
        assert isinstance(t.getFromState(), StandardState)
        assert isinstance(t.getToState(), StandardState)

    def test_transitions_are_standard_state_transition_info(self):
        wrapper = _make_wrapper([{"from_state": "X", "to_state": "Y", "sojourn_sec": 1}])
        t = JsonLogParsingStrategy().createLogFile(wrapper).getStateTransitionInfoList()[0]
        assert isinstance(t, StandardStateTransitionInfo)

    def test_empty_wrapper_returns_empty_list(self):
        wrapper = _make_wrapper([])
        transitions = JsonLogParsingStrategy().createLogFile(wrapper).getStateTransitionInfoList()
        assert transitions == []

    def test_preserves_order_of_transitions(self):
        records = [
            {"from_state": "A", "to_state": "B", "sojourn_sec": 1},
            {"from_state": "B", "to_state": "C", "sojourn_sec": 2},
            {"from_state": "C", "to_state": "A", "sojourn_sec": 3},
        ]
        wrapper = _make_wrapper(records)
        transitions = JsonLogParsingStrategy().createLogFile(wrapper).getStateTransitionInfoList()
        assert transitions[0].getFromState().getName() == "A"
        assert transitions[1].getFromState().getName() == "B"
        assert transitions[2].getFromState().getName() == "C"

    def test_multiple_same_pair_transitions(self):
        records = [{"from_state": "A", "to_state": "B", "sojourn_sec": i} for i in range(5)]
        wrapper = _make_wrapper(records)
        transitions = JsonLogParsingStrategy().createLogFile(wrapper).getStateTransitionInfoList()
        assert len(transitions) == 5
        sojourn_times = [t.getSojournTime() for t in transitions]
        assert sojourn_times == list(range(5))


# ---------------------------------------------------------------------------
# Integration with real files
# ---------------------------------------------------------------------------

class TestJsonLogParsingStrategyIntegration:
    def test_normal_file_produces_correct_state_set(self, normal_file_path):
        reader = JsonFileReadingStrategy()
        parser = JsonLogParsingStrategy()
        transitions = parser.createLogFile(reader.readFile(normal_file_path)).getStateTransitionInfoList()
        state_names = set()
        for t in transitions:
            state_names.add(t.getFromState().getName())
            state_names.add(t.getToState().getName())
        # normal files use state1/state2/state3
        assert "state1" in state_names
        assert "state2" in state_names

    def test_all_sojourn_times_are_non_negative(self, normal_file_path):
        reader = JsonFileReadingStrategy()
        parser = JsonLogParsingStrategy()
        transitions = parser.createLogFile(reader.readFile(normal_file_path)).getStateTransitionInfoList()
        assert all(t.getSojournTime() >= 0 for t in transitions)

    def test_transition_count_matches_line_count(self, normal_file_path):
        # Every line in the file should produce exactly one transition
        line_count = sum(1 for line in normal_file_path.read_text().splitlines() if line.strip())
        reader = JsonFileReadingStrategy()
        parser = JsonLogParsingStrategy()
        transitions = parser.createLogFile(reader.readFile(normal_file_path)).getStateTransitionInfoList()
        assert len(transitions) == line_count
