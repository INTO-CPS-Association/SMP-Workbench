import pytest

from src.interfaces.file_reading_strategy import FileReadingStrategy
from classes.json_file_reading_strategy import JsonFileReadingStrategy
from classes.json_file_wrapper import JsonFileWrapper


# ---------------------------------------------------------------------------
# Type contract
# ---------------------------------------------------------------------------

class TestJsonFileReadingStrategyType:
    def test_is_file_reading_strategy(self):
        assert isinstance(JsonFileReadingStrategy(), FileReadingStrategy)

    def test_read_returns_json_file_wrapper(self, tmp_json_file):
        result = JsonFileReadingStrategy().readFile(tmp_json_file)
        assert isinstance(result, JsonFileWrapper)

    def test_raises_os_error_on_txt_extension(self, tmp_non_json_file):
        with pytest.raises(OSError):
            JsonFileReadingStrategy().readFile(tmp_non_json_file)

    def test_os_error_message_is_descriptive(self, tmp_non_json_file):
        with pytest.raises(OSError) as exc:
            JsonFileReadingStrategy().readFile(tmp_non_json_file)
        assert "did not end with .json" in str(exc.value).lower() or ".json" in str(exc.value)


# ---------------------------------------------------------------------------
# Parsing behaviour
# ---------------------------------------------------------------------------

class TestJsonFileReadingStrategyParsing:
    def test_valid_file_returns_correct_number_of_objects(self, tmp_json_file):
        wrapper = JsonFileReadingStrategy().readFile(tmp_json_file)
        assert len(wrapper.getObjectList()) == 4

    def test_parsed_objects_are_dicts(self, tmp_json_file):
        wrapper = JsonFileReadingStrategy().readFile(tmp_json_file)
        for obj in wrapper.getObjectList():
            assert isinstance(obj, dict)

    def test_parsed_objects_contain_expected_keys(self, tmp_json_file):
        wrapper = JsonFileReadingStrategy().readFile(tmp_json_file)
        for obj in wrapper.getObjectList():
            assert "from_state" in obj
            assert "to_state" in obj
            assert "sojourn_sec" in obj

    def test_non_json_lines_are_silently_skipped(self, tmp_json_file_with_noise):
        wrapper = JsonFileReadingStrategy().readFile(tmp_json_file_with_noise)
        # The fixture has 2 valid JSON lines and 2 non-JSON lines
        assert len(wrapper.getObjectList()) == 2

    def test_empty_file_returns_empty_list(self, tmp_empty_json_file):
        wrapper = JsonFileReadingStrategy().readFile(tmp_empty_json_file)
        assert wrapper.getObjectList() == []

    def test_blank_lines_are_skipped(self, tmp_path):
        p = tmp_path / "blanks.json"
        p.write_text(
            "\n"
            '{"from_state": "A", "to_state": "B", "sojourn_sec": 5}\n'
            "\n\n"
            '{"from_state": "B", "to_state": "A", "sojourn_sec": 10}\n'
            "\n"
        )
        wrapper = JsonFileReadingStrategy().readFile(p)
        assert len(wrapper.getObjectList()) == 2

    def test_malformed_json_line_is_skipped(self, tmp_path):
        p = tmp_path / "malformed.json"
        p.write_text(
            '{"from_state": "A", "to_state": "B", "sojourn_sec": 5}\n'
            "not valid json at all\n"
            '{"from_state": "B", "to_state": "A", "sojourn_sec": 10}\n'
        )
        wrapper = JsonFileReadingStrategy().readFile(p)
        assert len(wrapper.getObjectList()) == 2

    def test_parsed_values_match_written_values(self, tmp_path):
        p = tmp_path / "exact.json"
        p.write_text('{"from_state": "Idle", "to_state": "Dosing", "sojourn_sec": 42}\n')
        obj = JsonFileReadingStrategy().readFile(p).getObjectList()[0]
        assert obj["from_state"] == "Idle"
        assert obj["to_state"] == "Dosing"
        assert obj["sojourn_sec"] == 42

    def test_real_normal_file_parses_without_error(self, normal_file_path):
        wrapper = JsonFileReadingStrategy().readFile(normal_file_path)
        assert len(wrapper.getObjectList()) > 0

    def test_real_outlier_file_parses_without_error(self, outlier_file_path):
        wrapper = JsonFileReadingStrategy().readFile(outlier_file_path)
        assert len(wrapper.getObjectList()) > 0
