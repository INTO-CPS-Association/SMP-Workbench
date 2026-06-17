import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.routers.analysis import (
    _normalize_probabilities,
    _exclude_suspicious_files,
    _group_by_pair,
    _score_transitions,
)
from backend.schemas import SuspiciousTransitionEntry
from utils.statistics import calculateStatistics, StatisticsResult, QuarantinedEntry
from interfaces.state_transition_info import StateTransitionInfo
from interfaces.state_transition_statistics import StateTransitionStatistics

client = TestClient(app)

PRECISION = 1e-3


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _probability_sums(stats: list[StateTransitionStatistics]) -> dict[str, float]:
    sums: dict[str, float] = {}
    for s in stats:
        name = s.getFromState().getName()
        sums[name] = sums.get(name, 0.0) + s.getProbability()
    return sums


def _total_accounted(result: StatisticsResult) -> int:
    return sum(len(s.getSojournTimes()) for s in result.statistics) + len(result.quarantined)


def _upload(paths: list[Path]) -> list[tuple]:
    return [
        ("files", (p.name, p.read_bytes(), "application/json"))
        for p in paths
    ]


# ---------------------------------------------------------------------------
# calculateStatistics â€” fixed tuple-unpack bug (was: stats, q = calculateStatistics(...))
# ---------------------------------------------------------------------------

class TestCalculateStatisticsSingleFile:
    @pytest.fixture(autouse=True)
    def _load(self, normal_transitions):
        self.transitions = normal_transitions
        self.result = calculateStatistics(self.transitions)

    def test_returns_non_empty_statistics(self):
        assert len(self.result.statistics) > 0

    def test_probabilities_sum_to_one_per_from_state(self):
        for state, total in _probability_sums(self.result.statistics).items():
            assert abs(total - 1.0) < PRECISION, f"{state}: sum={total}"

    def test_sojourn_times_are_non_negative(self):
        for s in self.result.statistics:
            assert all(t >= 0 for t in s.getSojournTimes())

    def test_all_transitions_accounted_for(self):
        assert _total_accounted(self.result) == len(self.transitions)

    def test_quarantined_is_list(self):
        assert isinstance(self.result.quarantined, list)


class TestCalculateStatisticsMultiFile:
    @pytest.fixture(autouse=True)
    def _load(self, normal_transitions, normal_transitions_2):
        self.transitions_a = normal_transitions
        self.transitions_b = normal_transitions_2
        self.combined = normal_transitions + normal_transitions_2
        self.result_a = calculateStatistics(self.transitions_a)
        self.result_b = calculateStatistics(self.transitions_b)
        self.result_combined = calculateStatistics(self.combined)

    def test_combined_at_least_as_many_pairs_as_either_file(self):
        assert len(self.result_combined.statistics) >= max(
            len(self.result_a.statistics), len(self.result_b.statistics)
        )

    def test_combined_probabilities_sum_to_one(self):
        for state, total in _probability_sums(self.result_combined.statistics).items():
            assert abs(total - 1.0) < PRECISION, f"{state}: sum={total}"

    def test_combined_all_transitions_accounted(self):
        assert _total_accounted(self.result_combined) == len(self.combined)

    def test_states_from_both_files_in_combined(self):
        def names(result: StatisticsResult) -> set[str]:
            s: set[str] = set()
            for stat in result.statistics:
                s.add(stat.getFromState().getName())
                s.add(stat.getToState().getName())
            return s

        assert names(self.result_a).issubset(names(self.result_combined))
        assert names(self.result_b).issubset(names(self.result_combined))


# ---------------------------------------------------------------------------
# _normalize_probabilities
# ---------------------------------------------------------------------------

class TestNormalizeProbabilities:
    def test_single_edge_per_source_unchanged(self):
        edges = [{"source": "A", "target": "B", "probability": 1.0}]
        _normalize_probabilities(edges)
        assert edges[0]["probability"] == pytest.approx(1.0)

    def test_two_edges_sum_to_exactly_one(self):
        edges = [
            {"source": "A", "target": "B", "probability": 0.3333},
            {"source": "A", "target": "C", "probability": 0.6667},
        ]
        _normalize_probabilities(edges)
        total = sum(e["probability"] for e in edges)
        assert total == pytest.approx(1.0)

    def test_rounding_drift_absorbed_into_last_edge(self):
        # 1/3 rounded to 4 decimals three times sums to 0.9999 before fix
        edges = [
            {"source": "A", "target": "B", "probability": 0.3333},
            {"source": "A", "target": "C", "probability": 0.3333},
            {"source": "A", "target": "D", "probability": 0.3333},
        ]
        _normalize_probabilities(edges)
        total = sum(e["probability"] for e in edges)
        assert total == pytest.approx(1.0)

    def test_multiple_source_states_each_sum_to_one(self):
        edges = [
            {"source": "A", "target": "B", "probability": 0.4999},
            {"source": "A", "target": "C", "probability": 0.5001},
            {"source": "B", "target": "A", "probability": 0.9998},
            {"source": "B", "target": "C", "probability": 0.0002},
        ]
        _normalize_probabilities(edges)
        sums: dict[str, float] = {}
        for e in edges:
            sums[e["source"]] = sums.get(e["source"], 0.0) + e["probability"]
        for src, total in sums.items():
            assert total == pytest.approx(1.0), f"{src}: {total}"


# ---------------------------------------------------------------------------
# _exclude_suspicious_files
# ---------------------------------------------------------------------------

class TestExcludeSuspiciousFiles:
    def test_no_suspicious_returns_all(self, normal_transitions):
        file_info = {"file1.json": normal_transitions}
        result = _exclude_suspicious_files(file_info, set())
        assert len(result) == len(normal_transitions)

    def test_suspicious_file_excluded(self, normal_transitions):
        file_info = {
            "clean.json": normal_transitions,
            "bad.json": normal_transitions,
        }
        result = _exclude_suspicious_files(file_info, {"bad.json"})
        assert len(result) == len(normal_transitions)

    def test_all_files_suspicious_returns_empty(self, normal_transitions):
        file_info = {"a.json": normal_transitions, "b.json": normal_transitions}
        result = _exclude_suspicious_files(file_info, {"a.json", "b.json"})
        assert result == []


# ---------------------------------------------------------------------------
# _group_by_pair (router version)
# ---------------------------------------------------------------------------

class TestRouterGroupByPair:
    def test_groups_transitions_by_pair(self, normal_transitions):
        groups = _group_by_pair(normal_transitions)
        # Every key is a (str, str) tuple
        for key in groups:
            assert isinstance(key, tuple) and len(key) == 2

    def test_all_transitions_present_in_groups(self, normal_transitions):
        groups = _group_by_pair(normal_transitions)
        total = sum(len(v) for v in groups.values())
        assert total == len(normal_transitions)


# ---------------------------------------------------------------------------
# _score_transitions
# ---------------------------------------------------------------------------

class TestScoreTransitions:
    def _make_entries(self, pairs_and_times: list) -> list[SuspiciousTransitionEntry]:
        return [
            SuspiciousTransitionEntry(fromState=fn, toState=tn, sojournTime=float(t))
            for fn, tn, t in pairs_and_times
        ]

    def test_output_length_matches_input(self):
        entries = self._make_entries([("A", "B", i * 10) for i in range(1, 7)])
        result = _score_transitions(entries)
        assert len(result) == len(entries)

    def test_all_entries_have_outlier_score(self):
        entries = self._make_entries([("A", "B", i * 10) for i in range(1, 7)])
        result = _score_transitions(entries)
        for r in result:
            assert isinstance(r.outlierScore, float)

    def test_all_entries_have_is_outlier(self):
        entries = self._make_entries([("A", "B", i * 10) for i in range(1, 7)])
        result = _score_transitions(entries)
        for r in result:
            assert isinstance(r.isOutlier, bool)

    def test_from_and_to_states_preserved(self):
        entries = self._make_entries([("X", "Y", 10), ("X", "Y", 20)])
        result = _score_transitions(entries)
        assert all(r.fromState == "X" and r.toState == "Y" for r in result)

    def test_iqr_method_accepted(self):
        entries = self._make_entries([("A", "B", i * 5) for i in range(1, 7)])
        result = _score_transitions(entries, method="iqr")
        assert len(result) == len(entries)


# ---------------------------------------------------------------------------
# POST /api/analyze
# ---------------------------------------------------------------------------

class TestAnalyzeEndpoint:
    def test_single_file_returns_200(self, normal_file_path):
        resp = client.post("/api/analyze", files=_upload([normal_file_path]))
        assert resp.status_code == 200

    def test_response_has_nodes_edges_quarantined(self, normal_file_path):
        data = client.post("/api/analyze", files=_upload([normal_file_path])).json()
        assert "nodes" in data
        assert "edges" in data
        assert "quarantined" in data

    def test_nodes_are_non_empty(self, normal_file_path):
        data = client.post("/api/analyze", files=_upload([normal_file_path])).json()
        assert len(data["nodes"]) > 0

    def test_edges_are_non_empty(self, normal_file_path):
        data = client.post("/api/analyze", files=_upload([normal_file_path])).json()
        assert len(data["edges"]) > 0

    def test_nodes_have_id_and_label(self, normal_file_path):
        data = client.post("/api/analyze", files=_upload([normal_file_path])).json()
        for node in data["nodes"]:
            assert "id" in node
            assert "label" in node

    def test_edges_have_required_fields(self, normal_file_path):
        data = client.post("/api/analyze", files=_upload([normal_file_path])).json()
        required = {"id", "source", "target", "probability", "avgSojournTime",
                    "transitionCount", "cleanSojournTimes"}
        for edge in data["edges"]:
            assert required.issubset(edge.keys())

    def test_edges_include_clean_sojourn_times(self, normal_file_path):
        data = client.post("/api/analyze", files=_upload([normal_file_path])).json()
        for edge in data["edges"]:
            assert isinstance(edge["cleanSojournTimes"], list)

    def test_edge_probabilities_sum_to_one_per_source(self, normal_file_path):
        data = client.post("/api/analyze", files=_upload([normal_file_path])).json()
        sums: dict[str, float] = {}
        for edge in data["edges"]:
            src = edge["source"]
            sums[src] = sums.get(src, 0.0) + edge["probability"]
        for src, total in sums.items():
            assert abs(total - 1.0) < PRECISION, f"{src}: {total}"

    def test_multi_file_returns_200(self, normal_file_path, normal_file_path_2):
        resp = client.post("/api/analyze", files=_upload([normal_file_path, normal_file_path_2]))
        assert resp.status_code == 200

    def test_multi_file_edge_probabilities_sum_to_one(self, normal_file_path, normal_file_path_2):
        data = client.post(
            "/api/analyze", files=_upload([normal_file_path, normal_file_path_2])
        ).json()
        sums: dict[str, float] = {}
        for edge in data["edges"]:
            src = edge["source"]
            sums[src] = sums.get(src, 0.0) + edge["probability"]
        for src, total in sums.items():
            assert abs(total - 1.0) < PRECISION, f"{src}: {total}"

    def test_multi_file_at_least_as_many_edges_as_single(self, normal_file_path, normal_file_path_2):
        single = client.post("/api/analyze", files=_upload([normal_file_path])).json()
        multi = client.post(
            "/api/analyze", files=_upload([normal_file_path, normal_file_path_2])
        ).json()
        assert len(multi["edges"]) >= len(single["edges"])

    def test_empty_upload_returns_422(self):
        resp = client.post("/api/analyze", files=[])
        assert resp.status_code == 422

    def test_quarantined_entries_have_required_fields(self, normal_file_path):
        data = client.post("/api/analyze", files=_upload([normal_file_path])).json()
        for q in data["quarantined"]:
            assert "fromState" in q
            assert "toState" in q
            assert "sojournTime" in q
            assert "outlierScore" in q


# ---------------------------------------------------------------------------
# POST /api/analyze/stream
# ---------------------------------------------------------------------------

class TestAnalyzeStreamEndpoint:
    def _parse_sse(self, text: str) -> list[dict]:
        events = []
        for block in text.split("\n\n"):
            for line in block.splitlines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
        return events

    def test_returns_200(self, normal_file_path):
        resp = client.post("/api/analyze/stream", files=_upload([normal_file_path]))
        assert resp.status_code == 200

    def test_final_event_has_result(self, normal_file_path):
        resp = client.post("/api/analyze/stream", files=_upload([normal_file_path]))
        events = self._parse_sse(resp.text)
        final = events[-1]
        assert "result" in final

    def test_result_has_nodes_and_edges(self, normal_file_path):
        resp = client.post("/api/analyze/stream", files=_upload([normal_file_path]))
        result = self._parse_sse(resp.text)[-1]["result"]
        assert "nodes" in result
        assert "edges" in result

    def test_progress_events_have_percent(self, normal_file_path):
        resp = client.post("/api/analyze/stream", files=_upload([normal_file_path]))
        events = self._parse_sse(resp.text)
        progress = [e for e in events if "percent" in e]
        assert len(progress) > 0

    def test_percent_reaches_100(self, normal_file_path):
        resp = client.post("/api/analyze/stream", files=_upload([normal_file_path]))
        events = self._parse_sse(resp.text)
        percents = [e["percent"] for e in events if "percent" in e]
        assert max(percents) == 100

    def test_stream_edge_probabilities_sum_to_one(self, normal_file_path):
        resp = client.post("/api/analyze/stream", files=_upload([normal_file_path]))
        edges = self._parse_sse(resp.text)[-1]["result"]["edges"]
        sums: dict[str, float] = {}
        for edge in edges:
            src = edge["source"]
            sums[src] = sums.get(src, 0.0) + edge["probability"]
        for src, total in sums.items():
            assert abs(total - 1.0) < PRECISION, f"{src}: {total}"


# ---------------------------------------------------------------------------
# POST /api/analyze/sojourn-outliers
# ---------------------------------------------------------------------------

class TestSojournOutliersEndpoint:
    def _body(self, pairs_and_times: list, method: str = "lof") -> dict:
        return {
            "transitions": [
                {"fromState": fn, "toState": tn, "sojournTime": float(t)}
                for fn, tn, t in pairs_and_times
            ],
            "method": method,
        }

    def test_returns_200(self):
        body = self._body([("A", "B", i * 10) for i in range(1, 7)])
        resp = client.post("/api/analyze/sojourn-outliers", json=body)
        assert resp.status_code == 200

    def test_response_length_matches_input(self):
        pairs = [("A", "B", i * 10) for i in range(1, 7)]
        body = self._body(pairs)
        result = client.post("/api/analyze/sojourn-outliers", json=body).json()
        assert len(result) == len(pairs)

    def test_entries_have_outlier_score(self):
        body = self._body([("A", "B", i * 10) for i in range(1, 7)])
        result = client.post("/api/analyze/sojourn-outliers", json=body).json()
        for entry in result:
            assert "outlierScore" in entry

    def test_entries_have_is_outlier(self):
        body = self._body([("A", "B", i * 10) for i in range(1, 7)])
        result = client.post("/api/analyze/sojourn-outliers", json=body).json()
        for entry in result:
            assert "isOutlier" in entry

    def test_iqr_method_accepted(self):
        body = self._body([("A", "B", i * 10) for i in range(1, 7)], method="iqr")
        resp = client.post("/api/analyze/sojourn-outliers", json=body)
        assert resp.status_code == 200

    def test_states_preserved_in_response(self):
        body = self._body([("X", "Y", 10), ("X", "Y", 20), ("X", "Y", 30)])
        result = client.post("/api/analyze/sojourn-outliers", json=body).json()
        for entry in result:
            assert entry["fromState"] == "X"
            assert entry["toState"] == "Y"
