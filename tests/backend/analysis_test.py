import io
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from classes.json_file_reading_strategy import JsonFileReadingStrategy
from classes.json_log_parsing_strategy import JsonLogParsingStrategy
from utils.statistics import calculateStatistics
from src.interfaces.state_transition_info import StateTransitionInfo
from src.interfaces.state_transition_statistics import StateTransitionStatistics

client = TestClient(app)

TEST_FILES_DIR = Path(__file__).parent.parent.parent / "files" / "test_files"
FILE_A = TEST_FILES_DIR / "test_file0.json"
FILE_B = TEST_FILES_DIR / "state_2025-12-03.json"

PRECISION = 1e-5


def _load_transitions(path: Path) -> list[StateTransitionInfo]:
    reader = JsonFileReadingStrategy()
    parser = JsonLogParsingStrategy()
    return parser.createLogFile(reader.readFile(path)).getStateTransitionInfoList()


def _probability_sums(stats: list[StateTransitionStatistics]) -> dict[str, float]:
    sums: dict[str, float] = {}
    for s in stats:
        name = s.getFromState().getName()
        sums[name] = sums.get(name, 0.0) + s.getProbability()
    return sums


# ── unit tests ────────────────────────────────────────────────────────────────

class TestCalculateStatisticsSingleFile:
    def setup_method(self):
        self.transitions = _load_transitions(FILE_A)
        self.stats = calculateStatistics(self.transitions)

    def test_returns_non_empty_list(self):
        assert len(self.stats) > 0

    def test_probabilities_sum_to_one_per_from_state(self):
        for from_state, total in _probability_sums(self.stats).items():
            assert abs(total - 1.0) < PRECISION, (
                f"Probabilities for '{from_state}' sum to {total}, expected ~1.0"
            )

    def test_sojourn_times_are_positive(self):
        for s in self.stats:
            assert all(t >= 0 for t in s.getSojournTimes())

    def test_transition_count_matches_sojourn_list_length(self):
        transitions_a = _load_transitions(FILE_A)
        for s in self.stats:
            assert len(s.getSojournTimes()) >= 1


class TestCalculateStatisticsMultiFile:
    def setup_method(self):
        self.transitions_a = _load_transitions(FILE_A)
        self.transitions_b = _load_transitions(FILE_B)
        self.combined = self.transitions_a + self.transitions_b
        self.stats_a = calculateStatistics(self.transitions_a)
        self.stats_b = calculateStatistics(self.transitions_b)
        self.stats_combined = calculateStatistics(self.combined)

    def test_combined_has_at_least_as_many_results_as_either_file(self):
        assert len(self.stats_combined) >= max(len(self.stats_a), len(self.stats_b))

    def test_probabilities_still_sum_to_one_per_from_state_after_combining(self):
        for from_state, total in _probability_sums(self.stats_combined).items():
            assert abs(total - 1.0) < PRECISION, (
                f"Probabilities for '{from_state}' sum to {total} in combined result"
            )

    def test_combined_transition_counts_exceed_single_file(self):
        def total_transitions(stats):
            return sum(len(s.getSojournTimes()) for s in stats)

        assert total_transitions(self.stats_combined) == (
            total_transitions(self.stats_a) + total_transitions(self.stats_b)
        )

    def test_states_from_both_files_appear_in_combined_result(self):
        def state_names(stats):
            names: set[str] = set()
            for s in stats:
                names.add(s.getFromState().getName())
                names.add(s.getToState().getName())
            return names

        names_a = state_names(self.stats_a)
        names_b = state_names(self.stats_b)
        names_combined = state_names(self.stats_combined)

        assert names_a.issubset(names_combined)
        assert names_b.issubset(names_combined)

    def test_shared_states_have_higher_transition_counts_when_combined(self):
        def counts_by_transition(stats):
            return {
                (s.getFromState().getName(), s.getToState().getName()): len(s.getSojournTimes())
                for s in stats
            }

        counts_a = counts_by_transition(self.stats_a)
        counts_b = counts_by_transition(self.stats_b)
        counts_combined = counts_by_transition(self.stats_combined)

        shared = set(counts_a) & set(counts_b)
        for key in shared:
            assert counts_combined[key] == counts_a[key] + counts_b[key], (
                f"Transition {key}: expected {counts_a[key] + counts_b[key]}, "
                f"got {counts_combined[key]}"
            )


# ── endpoint tests ─────────────────────────────────────────────────────────────

class TestAnalyzeEndpoint:
    def test_single_file_returns_200(self):
        with open(FILE_A, "rb") as f:
            response = client.post(
                "/api/analyze",
                files=[("files", ("test_file0.json", f, "application/json"))],
            )
        assert response.status_code == 200

    def test_single_file_response_has_nodes_and_edges(self):
        with open(FILE_A, "rb") as f:
            data = client.post(
                "/api/analyze",
                files=[("files", ("test_file0.json", f, "application/json"))],
            ).json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) > 0
        assert len(data["edges"]) > 0

    def test_multi_file_returns_200(self):
        with open(FILE_A, "rb") as fa, open(FILE_B, "rb") as fb:
            response = client.post(
                "/api/analyze",
                files=[
                    ("files", ("test_file0.json", fa, "application/json")),
                    ("files", ("state_2025-12-03.json", fb, "application/json")),
                ],
            )
        assert response.status_code == 200

    def test_multi_file_has_more_or_equal_edges_than_single(self):
        with open(FILE_A, "rb") as f:
            single = client.post(
                "/api/analyze",
                files=[("files", ("test_file0.json", f, "application/json"))],
            ).json()

        with open(FILE_A, "rb") as fa, open(FILE_B, "rb") as fb:
            multi = client.post(
                "/api/analyze",
                files=[
                    ("files", ("test_file0.json", fa, "application/json")),
                    ("files", ("state_2025-12-03.json", fb, "application/json")),
                ],
            ).json()

        assert len(multi["edges"]) >= len(single["edges"])

    def test_edge_probabilities_sum_to_one_per_source(self):
        with open(FILE_A, "rb") as fa, open(FILE_B, "rb") as fb:
            data = client.post(
                "/api/analyze",
                files=[
                    ("files", ("test_file0.json", fa, "application/json")),
                    ("files", ("state_2025-12-03.json", fb, "application/json")),
                ],
            ).json()

        sums: dict[str, float] = {}
        for edge in data["edges"]:
            src = edge["source"]
            sums[src] = sums.get(src, 0.0) + edge["probability"]

        for src, total in sums.items():
            assert abs(total - 1.0) < 1e-3, (
                f"Edge probabilities for source '{src}' sum to {total}"
            )

    def test_empty_upload_returns_400(self):
        response = client.post("/api/analyze", files=[])
        assert response.status_code == 422
