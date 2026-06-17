import numpy as np
from dataclasses import dataclass
from sklearn.neighbors import LocalOutlierFactor

theta = 0.2  # Weight-boost threshold: scores below this are boosted; above it are penalised
alpha = 0.2  # Learning rate for the weight vector update

OUTLIER_THRESHOLD = 0.85
_MIN_SAMPLES = 4  # LOF with n_neighbors=3 needs at least 4 samples


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------

@dataclass
class OutlierResult:
    """Outcome of running the adaptive LOF ensemble on a sequence of values."""
    # True for each entry whose normalised score exceeds OUTLIER_THRESHOLD
    is_outlier: list
    # Normalised anomaly score in [0, 1] for every entry in the input
    scores: list


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def calc_WB(score: float) -> float:
    """Computes the weight-boost value for a single LOF score.

    Points well below the outlier boundary (score < theta) receive a weight
    proportional to their score, keeping genuinely normal points sampled
    frequently.  Points above theta are down-weighted so the ensemble does not
    over-sample known outliers in later iterations.
    """
    if score < theta:
        return score / theta
    return (1 - score) / (1 - theta)


def _safe_lof_k(D_t: np.ndarray) -> int:
    """Returns a safe n_neighbors value for LOF on the subsample D_t.

    k must be at least as large as the most common duplicate count so that
    every point's neighbourhood extends past the block of identical values,
    preventing zero reachability distances that break the LOF density ratio.
    Returns 0 if a valid k cannot be found.
    """
    _, dup_counts = np.unique(D_t, return_counts=True)
    if len(dup_counts) < 2:
        # All values identical — LOF is undefined for this subsample
        return 0
    k = min(max(3, int(dup_counts.max())), len(D_t) - 1)
    return k if k >= 1 else 0


def _normalise(arr: np.ndarray) -> np.ndarray:
    """Linearly rescales arr to [0, 1]; returns a zero array if all values are equal."""
    rng = arr.max() - arr.min()
    return (arr - arr.min()) / rng if rng > 0 else np.zeros_like(arr)


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------

def analyze_anomalies(input: list[int], iter_count: int) -> list[float]:
    """Runs the adaptive sampling LOF ensemble and returns a raw anomaly score per entry.

    Each iteration draws a weighted subsample, scores it with LOF, then updates
    the per-entry weight so that points already identified as anomalous are sampled
    less aggressively in the next round.  The accumulated score H[i] reflects how
    consistently entry i was flagged across all iterations.
    """
    D = np.array(input).reshape(-1, 1)
    n = len(D)
    weight_vector = [1 / n] * n   # Start with a uniform sampling distribution
    N = 2 * n                      # Subsample size — twice the dataset length
    H = [0.0] * n                  # Accumulated anomaly scores, one per entry
    tau = 0.95                     # Score threshold for counting high-confidence outliers

    for _ in range(iter_count):
        # Normalise weights to a probability distribution
        p_t = [w / sum(weight_vector) for w in weight_vector]

        # Draw a weighted subsample and remove duplicates
        indices = list(set(np.random.choice(n, size=N, p=p_t, replace=True)))
        D_t = D[indices]

        k = _safe_lof_k(D_t)
        if k == 0:
            continue

        lof = LocalOutlierFactor(n_neighbors=k)
        lof.fit(D_t)
        score_t = _normalise(-lof.negative_outlier_factor_)

        # beta dampens the score contribution when many points look like outliers,
        # reducing noise from degenerate subsamples
        a_t = sum(1 for s in score_t if s > tau)
        beta = 1 - (a_t / len(D_t))

        for i, index in enumerate(indices):
            H[index] += beta * score_t[i]
            weight_vector[index] = (1 - alpha) * weight_vector[index] + alpha * calc_WB(score_t[i])

    return H


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_outliers_iqr(sojourn_times: list) -> OutlierResult:
    """IQR-based sojourn-time outlier detection.

    Flags every entry that lies above the upper fence Q3 + 1.5·IQR.
    Because IQR is a hard threshold (not a scoring method) all flagged
    entries receive outlierScore = 1.0 and clean entries receive 0.0.
    Returns all-clean when fewer than _MIN_SAMPLES values are supplied or
    when the IQR is zero (all values identical).
    """
    n = len(sojourn_times)
    if n < _MIN_SAMPLES:
        return OutlierResult(is_outlier=[False] * n, scores=[0.0] * n)

    arr = np.array(sojourn_times, dtype=float)
    q1, q3 = float(np.percentile(arr, 25)), float(np.percentile(arr, 75))
    iqr = q3 - q1
    if iqr == 0:
        return OutlierResult(is_outlier=[False] * n, scores=[0.0] * n)

    upper_fence = q3 + 1.5 * iqr
    is_outlier = [float(v) > upper_fence for v in sojourn_times]
    scores     = [1.0 if o else 0.0 for o in is_outlier]
    return OutlierResult(is_outlier=is_outlier, scores=scores)


def detect_outliers_with_scores(sojourn_times: list, iter_count: int = 20) -> OutlierResult:
    """Runs the ensemble on sojourn_times and returns flags and scores for every entry.

    Entries with fewer than _MIN_SAMPLES values are returned as all-clean because
    LOF requires at least n_neighbors + 1 points to produce meaningful scores.
    """
    n = len(sojourn_times)
    if n < _MIN_SAMPLES:
        return OutlierResult(is_outlier=[False] * n, scores=[0.0] * n)

    H = analyze_anomalies(sojourn_times, iter_count)
    H_norm = _normalise(np.array(H, dtype=float))
    return OutlierResult(
        is_outlier=[float(s) > OUTLIER_THRESHOLD for s in H_norm],
        scores=[float(s) for s in H_norm],
    )


def detect_suspicious_files(
    file_counts: dict[str, dict[tuple[str, str], int]],
    method: str = 'iqr',
) -> list[dict]:
    """Flags files whose count of a (from, to) transition is anomalously high across all files.

    method='iqr'  — IQR fence (Q3 + 1.5·IQR); reliable even with very few files.
    method='lof'  — Adaptive LOF ensemble on the per-pair count vectors; requires
                    at least _MIN_SAMPLES files.

    Only counts above the fence/threshold AND above the mean are flagged.
    Every flagged entry includes allCounts and allFilenames (parallel lists) so the
    frontend can identify which file each dot in the distribution plot represents.
    """
    if len(file_counts) < _MIN_SAMPLES:
        return []

    filenames = list(file_counts.keys())
    all_pairs: set[tuple[str, str]] = set()
    for counts in file_counts.values():
        all_pairs.update(counts.keys())

    flagged: list[dict] = []
    for pair in sorted(all_pairs):
        counts_vec = np.array([file_counts[fn].get(pair, 0) for fn in filenames], dtype=float)
        avg         = float(counts_vec.mean())
        counts_list = [int(c) for c in counts_vec]

        if method == 'lof':
            outlier_result = detect_outliers_with_scores(counts_vec.tolist())
            for fn, raw, is_out in zip(filenames, counts_vec, outlier_result.is_outlier):
                count = int(raw)
                if is_out and count > avg:
                    flagged.append({
                        "filename":     fn,
                        "transition":   f"{pair[0]} → {pair[1]}",
                        "fromState":    pair[0],
                        "toState":      pair[1],
                        "count":        count,
                        "avgCount":     round(avg, 2),
                        "allCounts":    counts_list,
                        "allFilenames": filenames,
                    })
        else:  # iqr (default)
            q1, q3      = float(np.percentile(counts_vec, 25)), float(np.percentile(counts_vec, 75))
            upper_fence = q3 + 1.5 * (q3 - q1)
            for fn, raw in zip(filenames, counts_vec):
                count = int(raw)
                if count > upper_fence and count > avg:
                    flagged.append({
                        "filename":     fn,
                        "transition":   f"{pair[0]} → {pair[1]}",
                        "fromState":    pair[0],
                        "toState":      pair[1],
                        "count":        count,
                        "avgCount":     round(avg, 2),
                        "allCounts":    counts_list,
                        "allFilenames": filenames,
                    })

    return flagged


if __name__ == '__main__':
    res = analyze_anomalies([1, 2, 3, 5, 6, 7, 13, 51], 20)
    print("res", res)
