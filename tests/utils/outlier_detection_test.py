import numpy as np
import pytest

from utils.outlier_detection import (
    calc_WB,
    _safe_lof_k,
    _normalise,
    analyze_anomalies,
    detect_outliers_iqr,
    detect_outliers_with_scores,
    detect_suspicious_files,
    OutlierResult,
    OUTLIER_THRESHOLD,
    _MIN_SAMPLES,
    theta,
)


# ---------------------------------------------------------------------------
# calc_WB
# ---------------------------------------------------------------------------

class TestCalcWB:
    def test_score_zero_returns_zero(self):
        assert calc_WB(0.0) == pytest.approx(0.0)

    def test_score_one_returns_zero(self):
        assert calc_WB(1.0) == pytest.approx(0.0)

    def test_score_equals_theta_boundary(self):
        # At exactly theta both branches should agree: score/theta == 1.0
        assert calc_WB(theta) == pytest.approx(1.0)

    def test_score_below_theta_increases_with_score(self):
        # Lower scores are sampled less; higher (but still clean) scores more
        assert calc_WB(0.05) < calc_WB(0.15)

    def test_score_above_theta_decreases_with_score(self):
        # Outlier scores are progressively down-weighted
        assert calc_WB(0.5) > calc_WB(0.9)

    def test_output_in_range_zero_to_one(self):
        for s in np.linspace(0.0, 1.0, 20):
            assert 0.0 <= calc_WB(float(s)) <= 1.0


# ---------------------------------------------------------------------------
# _safe_lof_k
# ---------------------------------------------------------------------------

class TestSafeLofK:
    def test_all_identical_returns_zero(self):
        assert _safe_lof_k(np.array([5, 5, 5, 5, 5])) == 0

    def test_single_unique_returns_zero(self):
        assert _safe_lof_k(np.array([1])) == 0

    def test_two_unique_values_returns_nonzero(self):
        k = _safe_lof_k(np.array([1, 2, 1, 2, 1]))
        assert k > 0

    def test_k_at_least_3_when_multiple_unique(self):
        arr = np.array([1, 2, 3, 4, 5])
        assert _safe_lof_k(arr) >= 3

    def test_k_does_not_exceed_array_length_minus_one(self):
        arr = np.array([1, 2, 3, 4, 5])
        k = _safe_lof_k(arr)
        assert k <= len(arr) - 1

    def test_k_exceeds_max_duplicate_count(self):
        # If 3 copies of one value exist, k must be >= 3 so neighbours extend past duplicates
        arr = np.array([1, 1, 1, 2, 3])
        k = _safe_lof_k(arr)
        assert k >= 3


# ---------------------------------------------------------------------------
# _normalise
# ---------------------------------------------------------------------------

class TestNormalise:
    def test_all_equal_returns_zeros(self):
        arr = np.array([7.0, 7.0, 7.0])
        result = _normalise(arr)
        assert np.allclose(result, 0.0)

    def test_min_maps_to_zero(self):
        arr = np.array([1.0, 5.0, 10.0])
        result = _normalise(arr)
        assert result.min() == pytest.approx(0.0)

    def test_max_maps_to_one(self):
        arr = np.array([1.0, 5.0, 10.0])
        result = _normalise(arr)
        assert result.max() == pytest.approx(1.0)

    def test_middle_value_scaled_correctly(self):
        arr = np.array([0.0, 5.0, 10.0])
        result = _normalise(arr)
        assert result[1] == pytest.approx(0.5)

    def test_output_length_matches_input(self):
        arr = np.array([3.0, 1.0, 4.0, 1.0, 5.0])
        assert len(_normalise(arr)) == len(arr)


# ---------------------------------------------------------------------------
# analyze_anomalies
# ---------------------------------------------------------------------------

class TestAnalyzeAnomalies:
    def test_output_length_matches_input(self):
        data = [10, 11, 12, 13, 14, 15]
        result = analyze_anomalies(data, iter_count=5)
        assert len(result) == len(data)

    def test_returns_list_of_floats(self):
        result = analyze_anomalies([1, 2, 3, 4, 5], iter_count=5)
        assert all(isinstance(v, float) for v in result)

    def test_scores_are_non_negative(self):
        result = analyze_anomalies([10, 11, 12, 13, 14, 15], iter_count=10)
        assert all(v >= 0.0 for v in result)


# ---------------------------------------------------------------------------
# detect_outliers_iqr
# ---------------------------------------------------------------------------

class TestDetectOutliersIQR:
    def test_returns_outlier_result_type(self):
        result = detect_outliers_iqr([1, 2, 3, 4, 5])
        assert isinstance(result, OutlierResult)

    def test_fewer_than_min_samples_all_clean(self):
        data = list(range(_MIN_SAMPLES - 1))
        result = detect_outliers_iqr(data)
        assert all(not x for x in result.is_outlier)
        assert all(s == 0.0 for s in result.scores)

    def test_exactly_min_samples_is_processed(self):
        data = list(range(_MIN_SAMPLES))
        result = detect_outliers_iqr(data)
        assert len(result.is_outlier) == _MIN_SAMPLES

    def test_zero_iqr_all_identical_returns_all_clean(self):
        result = detect_outliers_iqr([5, 5, 5, 5, 5, 5])
        assert all(not x for x in result.is_outlier)

    def test_clear_outlier_is_flagged(self):
        # All values tight around 10; one extreme outlier
        data = [10, 11, 10, 12, 10, 11, 1000]
        result = detect_outliers_iqr(data)
        assert result.is_outlier[-1] is True

    def test_no_outliers_in_uniform_spread(self):
        data = list(range(1, 11))  # 1–10, no outliers
        result = detect_outliers_iqr(data)
        assert not any(result.is_outlier)

    def test_output_length_matches_input(self):
        data = [5, 6, 7, 8, 9, 100]
        result = detect_outliers_iqr(data)
        assert len(result.is_outlier) == len(data)
        assert len(result.scores) == len(data)

    def test_scores_are_binary(self):
        data = [10, 11, 10, 12, 10, 11, 1000]
        result = detect_outliers_iqr(data)
        assert all(s in (0.0, 1.0) for s in result.scores)

    def test_outlier_score_is_one(self):
        data = [10, 11, 10, 12, 10, 11, 1000]
        result = detect_outliers_iqr(data)
        assert result.scores[-1] == 1.0

    def test_is_outlier_and_scores_are_parallel(self):
        data = [10, 11, 12, 13, 14, 1000]
        result = detect_outliers_iqr(data)
        for is_out, score in zip(result.is_outlier, result.scores):
            expected_score = 1.0 if is_out else 0.0
            assert score == expected_score

    def test_only_above_upper_fence_flagged(self):
        # Q1=11.5, Q3=16.5, IQR=5, upper_fence=16.5+7.5=24
        data = [10, 11, 12, 13, 14, 19, 25]
        result = detect_outliers_iqr(data)
        # 25 > 24 → outlier; 19 <= 24 → clean
        assert result.is_outlier[5] is False   # 19
        assert result.is_outlier[6] is True    # 25

    def test_below_lower_fence_flagged(self):
        # A clear low-side outlier must be flagged too, not just high-side ones
        data = [10, 11, 10, 12, 10, 11, -1000]
        result = detect_outliers_iqr(data)
        assert result.is_outlier[-1] is True

    def test_both_fences_active_simultaneously(self):
        # One low outlier and one high outlier in the same sample should both be flagged
        data = [10, 11, 12, 13, 14, -1000, 1000]
        result = detect_outliers_iqr(data)
        assert result.is_outlier[5] is True   # -1000
        assert result.is_outlier[6] is True   # 1000
        assert not any(result.is_outlier[:5])


# ---------------------------------------------------------------------------
# detect_outliers_with_scores (LOF ensemble — structure tests only,
# since the algorithm is non-deterministic)
# ---------------------------------------------------------------------------

class TestDetectOutliersWithScores:
    def test_returns_outlier_result_type(self):
        result = detect_outliers_with_scores([1, 2, 3, 4, 5])
        assert isinstance(result, OutlierResult)

    def test_fewer_than_min_samples_all_clean(self):
        data = list(range(_MIN_SAMPLES - 1))
        result = detect_outliers_with_scores(data)
        assert all(not x for x in result.is_outlier)
        assert all(s == 0.0 for s in result.scores)

    def test_output_length_matches_input(self):
        data = [10, 11, 12, 13, 14, 15, 16, 17]
        result = detect_outliers_with_scores(data)
        assert len(result.is_outlier) == len(data)
        assert len(result.scores) == len(data)

    def test_scores_in_zero_to_one(self):
        data = [10, 11, 12, 13, 14, 15]
        result = detect_outliers_with_scores(data)
        assert all(0.0 <= s <= 1.0 for s in result.scores)

    def test_is_outlier_booleans(self):
        data = [10, 11, 12, 13, 14, 15]
        result = detect_outliers_with_scores(data)
        assert all(isinstance(x, bool) for x in result.is_outlier)

    def test_outlier_threshold_applied(self):
        data = [10, 11, 12, 13, 14, 15]
        result = detect_outliers_with_scores(data)
        for is_out, score in zip(result.is_outlier, result.scores):
            if is_out:
                assert score > OUTLIER_THRESHOLD

    def test_identical_values_all_clean(self):
        # All values equal → LOF cannot distinguish; algorithm should be stable
        result = detect_outliers_with_scores([5] * 10)
        assert all(not x for x in result.is_outlier)


# ---------------------------------------------------------------------------
# detect_suspicious_files
# ---------------------------------------------------------------------------

class TestDetectSuspiciousFiles:
    def _make_file_counts(self, mapping: dict) -> dict:
        """mapping: filename → {(from, to): count}"""
        return mapping

    def test_fewer_than_min_files_returns_empty(self):
        counts = {f"file{i}": {("A", "B"): 10} for i in range(_MIN_SAMPLES - 1)}
        assert detect_suspicious_files(counts) == []

    def test_exactly_min_files_is_processed(self):
        counts = {f"file{i}": {("A", "B"): i + 1} for i in range(_MIN_SAMPLES)}
        result = detect_suspicious_files(counts)
        assert isinstance(result, list)

    def test_uniform_counts_no_suspicious_files(self):
        # All files have exactly the same count — no outlier
        counts = {f"file{i}": {("A", "B"): 10} for i in range(6)}
        assert detect_suspicious_files(counts) == []

    def test_high_count_file_flagged_iqr(self):
        # One file has 10× the count of the others
        counts = {f"file{i}": {("A", "B"): 5} for i in range(5)}
        counts["outlier_file"] = {("A", "B"): 500}
        result = detect_suspicious_files(counts, method="iqr")
        filenames = [r["filename"] for r in result]
        assert "outlier_file" in filenames

    def test_low_count_file_flagged_iqr(self):
        # A file with a much lower count than the others must be flagged too
        counts = {f"file{i}": {("A", "B"): 100} for i in range(5)}
        counts["low_file"] = {("A", "B"): 1}
        result = detect_suspicious_files(counts, method="iqr")
        filenames = [r["filename"] for r in result]
        assert "low_file" in filenames

    def test_low_count_entry_below_avg(self):
        counts = {f"file{i}": {("A", "B"): 100} for i in range(5)}
        counts["low_file"] = {("A", "B"): 1}
        result = detect_suspicious_files(counts, method="iqr")
        entry = next(r for r in result if r["filename"] == "low_file")
        assert entry["count"] < entry["avgCount"]

    def test_mild_dip_not_flagged(self):
        # A count that's below average but within the fences (lower_fence=3.0) should not be flagged
        counts = {
            "file0": {("A", "B"): 10},
            "file1": {("A", "B"): 12},
            "file2": {("A", "B"): 14},
            "file3": {("A", "B"): 16},
            "file4": {("A", "B"): 18},
        }
        counts["mild_file"] = {("A", "B"): 9}
        result = detect_suspicious_files(counts, method="iqr")
        filenames = [r["filename"] for r in result]
        assert "mild_file" not in filenames

    def test_result_entries_have_required_keys(self):
        counts = {f"file{i}": {("A", "B"): 5} for i in range(5)}
        counts["outlier_file"] = {("A", "B"): 500}
        result = detect_suspicious_files(counts, method="iqr")
        required = {"filename", "transition", "fromState", "toState", "count", "avgCount",
                    "allCounts", "allFilenames"}
        for entry in result:
            assert required.issubset(entry.keys())

    def test_all_filenames_present_in_allFilenames(self):
        counts = {f"file{i}": {("A", "B"): 5} for i in range(5)}
        counts["outlier_file"] = {("A", "B"): 500}
        result = detect_suspicious_files(counts, method="iqr")
        all_input_files = set(counts.keys())
        for entry in result:
            assert all_input_files == set(entry["allFilenames"])

    def test_transition_string_formatted_correctly(self):
        counts = {f"file{i}": {("X", "Y"): 5} for i in range(5)}
        counts["outlier"] = {("X", "Y"): 500}
        result = detect_suspicious_files(counts, method="iqr")
        for entry in result:
            assert entry["transition"] == "X → Y"

    def test_count_above_avg_in_flagged_entry(self):
        counts = {f"file{i}": {("A", "B"): 5} for i in range(5)}
        counts["outlier_file"] = {("A", "B"): 500}
        result = detect_suspicious_files(counts, method="iqr")
        for entry in result:
            assert entry["count"] > entry["avgCount"]
