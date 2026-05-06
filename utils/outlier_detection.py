import numpy as np
from scipy import stats
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.neighbors import LocalOutlierFactor

# Outlier analysis function for 1D outlier analysis
# Uses the LOF (Local Outlier Factor) algorithm as bas
# D stands for dataset
# @0: List of integers
# Ret: List of integers with outlier scores for each element in D
theta = 0.2 # Threshold: [0,1]
alpha = 0.2


def analyze_anomalies(input: list[int], iter_count: int) -> list[float]:
    # Initialize the weight vector
    D = np.array(input).reshape(-1,1)
    weight_vector = [1/len(D) for x in range(len(D))]
    N = 2*len(D)
    H = [0.0]*len(D)
    beta = 0.0
    tau = 0.95

    # for t in T
    for t in range(iter_count):
    
        # 1. Obtain the probability distribution for sampling:
        p_t = [x / sum(weight_vector) for x in weight_vector]
        #print("p_t", p_t)

        # 2. Draw N observations from D (dataset) using p_t, remove duplicates
        indices = np.random.choice(len(D), size=N, p=p_t, replace=True)
        # Remove duplicates
        indices = list(set(indices))
        D_t = D[indices]

        # Skip iteration if all subsampled values are identical — LOF is undefined
        _, dup_counts = np.unique(D_t, return_counts=True)
        if len(dup_counts) < 2:
            continue

        # k must be >= the most-common value's count so that every point's
        # neighbourhood extends past the block of duplicates, preventing
        # zero reachability distances that break the LOF density ratio.
        k = min(max(3, int(dup_counts.max())), len(D_t) - 1)
        if k < 1:
            continue
        lof = LocalOutlierFactor(n_neighbors=k)

        # Fit
        lof.fit(D_t)
        score_t = -lof.negative_outlier_factor_

        # Normalize score_t
        rng = score_t.max() - score_t.min()
        score_t = (score_t - score_t.min()) / rng if rng > 0 else np.zeros_like(score_t)

        
        # Count number of scores that are greater than tau threshold
        a_t = sum(1 for score in score_t if score > tau)

        # Calculate beta
        beta = 1 - (a_t/len(D_t))

        # Sum final score and update weights
        for i, index in enumerate(indices):
            H[index] += beta * score_t[i]
            WB = calc_WB(score_t[i])
            weight_vector[index] = (1-alpha) * weight_vector[index] + alpha*WB

    return H

def calc_WB(score):
    if score < theta:
        return score/theta
    else:
        return (1-score)/(1-theta)

OUTLIER_THRESHOLD = 0.7
_MIN_SAMPLES = 4  # LOF with n_neighbors=3 needs at least 4 samples


def detect_outliers_with_scores(sojourn_times: list, iter_count: int = 20) -> tuple[list[bool], list[float]]:
    """Normalize H scores to [0,1] and flag entries above OUTLIER_THRESHOLD as outliers."""
    n = len(sojourn_times)
    if n < _MIN_SAMPLES:
        return [False] * n, [0.0] * n
    H = analyze_anomalies(sojourn_times, iter_count)
    H_arr = np.array(H, dtype=float)
    rng = H_arr.max() - H_arr.min()
    H_norm = (H_arr - H_arr.min()) / rng if rng > 0 else np.zeros_like(H_arr)
    is_outlier = [float(s) > OUTLIER_THRESHOLD for s in H_norm]
    return is_outlier, [float(s) for s in H_norm]


def detect_suspicious_files(
    file_counts: dict[str, dict[tuple[str, str], int]],
) -> list[dict]:
    """Flag files whose count of a (from, to) transition is an outlier-high value across all files."""
    if len(file_counts) < _MIN_SAMPLES:
        return []

    filenames = list(file_counts.keys())
    all_pairs: set[tuple[str, str]] = set()
    for counts in file_counts.values():
        all_pairs.update(counts.keys())

    flagged: list[dict] = []
    for pair in sorted(all_pairs):
        counts_vec = [file_counts[fn].get(pair, 0) for fn in filenames]
        is_outlier, scores = detect_outliers_with_scores(counts_vec)
        avg = sum(counts_vec) / len(counts_vec)
        for fn, count, outlier, score in zip(filenames, counts_vec, is_outlier, scores):
            if outlier and count > avg:
                flagged.append({
                    "filename": fn,
                    "transition": f"{pair[0]} → {pair[1]}",
                    "fromState": pair[0],
                    "toState": pair[1],
                    "count": count,
                    "avgCount": round(avg, 2),
                    "outlierScore": round(score, 4),
                })

    return flagged


if __name__ == '__main__':
    res = analyze_anomalies([1,2,3,5,6,7,13,51], 20)
    print("res", res)