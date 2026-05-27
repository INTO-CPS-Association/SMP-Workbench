import asyncio
import json
import os
import tempfile
import pathlib
from dataclasses import dataclass, field
from typing import AsyncGenerator, List

import numpy as np
from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from fastapi.responses import StreamingResponse

from classes.json_file_reading_strategy import JsonFileReadingStrategy
from classes.json_log_parsing_strategy import JsonLogParsingStrategy
from utils.statistics import calculateStatistics
from utils.outlier_detection import detect_outliers_with_scores, detect_outliers_iqr, detect_suspicious_files
from backend.schemas import AnalysisResponse, NodeSchema, EdgeSchema, QuarantinedEntrySchema, SuspiciousFileSchema, SuspiciousTransitionEntry, SojournOutliersRequest

router = APIRouter(prefix="/api", tags=["analysis"])


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class ParsedFile:
    """Everything extracted from one uploaded log file after parsing."""
    # StateTransitionInfo objects in order of occurrence
    transitions: list = field(default_factory=list)
    # Number of times each (from_state, to_state) pair occurs in this file
    counts: dict = field(default_factory=dict)
    # Lightweight (from_state, to_state, sojourn_time) tuples for the frontend
    raw_transitions: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pure helpers — each returns exactly one value
# ---------------------------------------------------------------------------

def _sse(payload: dict) -> str:
    """Formats a dict as a Server-Sent Events data line."""
    return f"data: {json.dumps(payload)}\n\n"


def _parse_temp_file(tmp_path: str, reader: JsonFileReadingStrategy, parser: JsonLogParsingStrategy) -> ParsedFile:
    """Reads the JSON at tmp_path, parses it into transitions, and collects pair counts."""
    file_wrapper = reader.readFile(pathlib.Path(tmp_path))
    log_file = parser.createLogFile(file_wrapper)
    transitions = log_file.getStateTransitionInfoList()

    counts: dict[tuple[str, str], int] = {}
    raw: list[tuple[str, str, float]] = []
    for info in transitions:
        fn = info.getFromState().getName()
        tn = info.getToState().getName()
        counts[(fn, tn)] = counts.get((fn, tn), 0) + 1
        raw.append((fn, tn, float(info.getSojournTime())))

    return ParsedFile(transitions=transitions, counts=counts, raw_transitions=raw)


def _attach_suspicious_transitions(
    suspicious_entries: list[dict],
    file_transitions: dict[str, list[tuple[str, str, float]]],
) -> list[dict]:
    """Returns suspicious file entries enriched with the raw transitions from that file.

    Sojourn-time outlier detection is NOT run here — it is deferred to the
    /analyze/sojourn-outliers endpoint, which is called only when the user
    chooses to re-include a suspicious file on the Statistics page.
    """
    seen: dict[str, list[dict]] = {}
    result = []
    for entry in suspicious_entries:
        filename = entry["filename"]
        if filename not in seen:
            seen[filename] = [
                {"fromState": f, "toState": t, "sojournTime": s}
                for f, t, s in file_transitions.get(filename, [])
            ]
        result.append({**entry, "transitions": seen[filename]})
    return result


def _pick_detector(method: str):
    """Returns the sojourn-time outlier detection callable for the given method name."""
    return detect_outliers_iqr if method == 'iqr' else detect_outliers_with_scores


def _score_transitions(
    transitions: List[SuspiciousTransitionEntry],
    method: str = 'lof',
) -> List[SuspiciousTransitionEntry]:
    """Groups transitions by (from, to) pair and runs sojourn-time outlier detection on each group.

    Returns the same list with outlierScore and isOutlier populated.
    Called inside asyncio.to_thread so the event loop stays free.
    """
    detector = _pick_detector(method)
    pair_indices: dict[tuple[str, str], list[int]] = {}
    for idx, t in enumerate(transitions):
        key = (t.fromState, t.toState)
        if key not in pair_indices:
            pair_indices[key] = []
        pair_indices[key].append(idx)

    results = [
        SuspiciousTransitionEntry(fromState=t.fromState, toState=t.toState, sojournTime=t.sojournTime)
        for t in transitions
    ]

    for indices in pair_indices.values():
        times = [transitions[i].sojournTime for i in indices]
        outlier_result = detector(times)
        for list_pos, orig_idx in enumerate(indices):
            results[orig_idx].outlierScore = round(outlier_result.scores[list_pos], 4)
            results[orig_idx].isOutlier = bool(outlier_result.is_outlier[list_pos])

    return results


def _exclude_suspicious_files(
    file_info: dict[str, list],
    suspicious_filenames: set[str],
) -> list:
    """Returns a flat list of transitions from every file that was NOT flagged as suspicious."""
    return [
        transition
        for filename, transitions in file_info.items()
        if filename not in suspicious_filenames
        for transition in transitions
    ]


def _group_by_pair(transitions: list) -> dict[tuple[str, str], list]:
    """Groups StateTransitionInfo objects by their (from_state, to_state) pair."""
    groups: dict[tuple[str, str], list] = {}
    for info in transitions:
        key = (info.getFromState().getName(), info.getToState().getName())
        if key not in groups:
            groups[key] = []
        groups[key].append(info)
    return groups


def _compute_from_counts(clean_by_pair: dict[tuple[str, str], list]) -> dict[str, int]:
    """Counts total clean transitions leaving each from-state.

    Used as the denominator when computing transition probabilities so that
    probabilities for all outgoing edges from a state sum to 1.
    """
    from_counts: dict[str, int] = {}
    for (fn, _), entries in clean_by_pair.items():
        from_counts[fn] = from_counts.get(fn, 0) + len(entries)
    return from_counts


def _normalize_probabilities(edges: list[dict]) -> None:
    """Adjusts the last outgoing edge per source state so probabilities sum exactly to 1.0000.

    Rounding each fraction independently (e.g. round(2/3, 4) + round(1/3, 4) = 1.0001)
    produces drift that would incorrectly trigger the probability-sum warning on the frontend.
    This pass absorbs the error into the last edge of each source group.
    """
    from_indices: dict[str, list[int]] = {}
    for i, edge in enumerate(edges):
        src = edge["source"]
        if src not in from_indices:
            from_indices[src] = []
        from_indices[src].append(i)

    for indices in from_indices.values():
        total = sum(edges[i]["probability"] for i in indices)
        if total != 1.0:
            last = indices[-1]
            edges[last]["probability"] = round(edges[last]["probability"] + (1.0 - total), 4)


def _build_edges(
    clean_by_pair: dict[tuple[str, str], list],
    from_counts: dict[str, int],
) -> list[dict]:
    """Builds the edge payload for every (from, to) pair using only clean transitions."""
    edges: list[dict] = []
    for (fn, tn), clean_entries in clean_by_pair.items():
        sojourn_times = [info.getSojournTime() for info in clean_entries]
        edges.append({
            "id": f"{fn}-{tn}",
            "source": fn,
            "target": tn,
            "probability": round(len(clean_entries) / from_counts[fn], 4),
            "avgSojournTime": round(float(np.average(sojourn_times)), 2),
            "transitionCount": len(sojourn_times),
            "cleanSojournTimes": [float(t) for t in sojourn_times],
        })
    _normalize_probabilities(edges)
    return edges


# ---------------------------------------------------------------------------
# Streaming endpoint
# ---------------------------------------------------------------------------

async def _stream_analysis(files: List[UploadFile], method: str = 'lof', file_method: str = 'iqr') -> AsyncGenerator[str, None]:
    reader = JsonFileReadingStrategy()
    parser = JsonLogParsingStrategy()
    file_info: dict[str, list] = {}
    file_transitions: dict[str, list[tuple[str, str, float]]] = {}
    file_counts: dict[str, dict[tuple[str, str], int]] = {}
    num_files = len(files)

    # Phase 1: read and parse each file (5 – 30 %)
    for i, upload in enumerate(files):
        yield _sse({"percent": int(5 + i / num_files * 25), "message": f"Reading file {i + 1} of {num_files}…"})
        filename = upload.filename or f"file_{i + 1}"
        content = await upload.read()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            parsed = _parse_temp_file(tmp_path, reader, parser)
            file_info[filename] = parsed.transitions
            file_counts[filename] = parsed.counts
            file_transitions[filename] = parsed.raw_transitions
        finally:
            os.unlink(tmp_path)

    if not any(file_info.values()):
        yield _sse({"error": "No valid transitions found in the uploaded files."})
        return

    # Phase 1.5: flag files with anomalously high transition counts (31 %)
    yield _sse({"percent": 31, "message": "Checking file consistency…"})
    raw_suspicious = await asyncio.to_thread(detect_suspicious_files, file_counts, file_method)
    suspicious_files = _attach_suspicious_transitions(raw_suspicious, file_transitions)
    suspicious_filenames = {sf["filename"] for sf in suspicious_files}

    # Phase 2: merge clean transitions and group by state pair (32 %)
    # Groups are built with per-entry file attribution so clean sojourn times can be
    # tracked per file and sent to the frontend for client-side file exclusion.
    yield _sse({"percent": 32, "message": "Grouping transitions…"})
    clean_file_info = {fn: v for fn, v in file_info.items() if fn not in suspicious_filenames}
    if not any(clean_file_info.values()):
        yield _sse({"error": "No valid transitions found in the uploaded files."})
        return

    groups: dict[tuple[str, str], list] = {}
    group_file_attr: dict[tuple[str, str], list[str]] = {}
    for filename, transitions in clean_file_info.items():
        for info in transitions:
            key = (info.getFromState().getName(), info.getToState().getName())
            if key not in groups:
                groups[key] = []
                group_file_attr[key] = []
            groups[key].append(info)
            group_file_attr[key].append(filename)

    # Phase 3: outlier detection per (from, to) pair (38 – 85 %)
    detector = _pick_detector(method)
    num_pairs = len(groups)
    quarantined_list: list[dict] = []
    clean_by_pair: dict[tuple[str, str], list] = {}
    # filename → edge_id → [clean sojourn times] — sent to frontend for client-side exclusion
    normal_file_times: dict[str, dict[str, list[float]]] = {}

    for pair_idx, ((fn, tn), entries) in enumerate(groups.items()):
        edge_id = f"{fn}-{tn}"
        file_attrs = group_file_attr[(fn, tn)]
        pct = int(38 + pair_idx / num_pairs * 47)
        yield _sse({"percent": pct, "message": f"Outlier detection: {fn} → {tn}  ({pair_idx + 1}/{num_pairs})"})
        sojourn_times = [info.getSojournTime() for info in entries]
        outlier_result = await asyncio.to_thread(detector, sojourn_times)

        clean = []
        for info, outlier, score in zip(entries, outlier_result.is_outlier, outlier_result.scores):
            if outlier:
                quarantined_list.append({
                    "fromState": fn, "toState": tn,
                    "sojournTime": float(info.getSojournTime()),
                    "outlierScore": round(score, 4),
                })
            else:
                clean.append(info)

        clean_by_pair[(fn, tn)] = clean if clean else list(entries)

        # Track per-file clean sojourn times (mirrors the fallback above)
        for info, fname, outlier in zip(entries, file_attrs, outlier_result.is_outlier):
            if not outlier or not clean:
                normal_file_times.setdefault(fname, {}).setdefault(edge_id, []).append(
                    float(info.getSojournTime())
                )

    # Phase 4: compute statistics and build the final response (86 – 100 %)
    yield _sse({"percent": 86, "message": "Computing statistics…"})
    from_counts = _compute_from_counts(clean_by_pair)
    edges = _build_edges(clean_by_pair, from_counts)
    state_names = {name for pair in clean_by_pair for name in pair}

    yield _sse({"percent": 95, "message": "Building response…"})
    nodes = [{"id": n, "label": n} for n in sorted(state_names)]
    # Ensure allFilenames is always present in suspicious file entries
    for sf in suspicious_files:
        sf.setdefault("allFilenames", [])

    normal_files_data = [
        {"filename": fname, "edgeTimes": edge_dict}
        for fname, edge_dict in normal_file_times.items()
    ]

    yield _sse({"percent": 100, "message": "Done!", "result": {
        "nodes": nodes,
        "edges": edges,
        "quarantined": quarantined_list,
        "suspiciousFiles": suspicious_files,
        "normalFiles": normal_files_data,
    }})


@router.post("/analyze/stream")
async def analyze_files_stream(
    files: List[UploadFile] = File(...),
    method: str = Query(default='lof', pattern='^(lof|iqr)$'),
    file_method: str = Query(default='iqr', pattern='^(lof|iqr)$'),
):
    return StreamingResponse(
        _stream_analysis(files, method, file_method),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/analyze/sojourn-outliers", response_model=List[SuspiciousTransitionEntry])
async def score_sojourn_outliers(body: SojournOutliersRequest):
    """Runs per-pair sojourn-time outlier detection on the supplied transitions.

    Called by the frontend when the user re-includes a suspicious file so that
    individual sojourn-time outliers within that file can be shown and excluded.
    """
    return await asyncio.to_thread(_score_transitions, body.transitions, body.method)


# ---------------------------------------------------------------------------
# Non-streaming endpoint (same logic, no SSE)
# ---------------------------------------------------------------------------

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_files(files: List[UploadFile] = File(...)):
    reader = JsonFileReadingStrategy()
    parser = JsonLogParsingStrategy()
    file_info: dict[str, list] = {}
    file_transitions: dict[str, list[tuple[str, str, float]]] = {}
    file_counts: dict[str, dict[tuple[str, str], int]] = {}

    for i, upload in enumerate(files):
        filename = upload.filename or f"file_{i + 1}"
        content = await upload.read()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            parsed = _parse_temp_file(tmp_path, reader, parser)
            file_info[filename] = parsed.transitions
            file_counts[filename] = parsed.counts
            file_transitions[filename] = parsed.raw_transitions
        finally:
            os.unlink(tmp_path)

    raw_suspicious = detect_suspicious_files(file_counts)
    suspicious_entries = _attach_suspicious_transitions(raw_suspicious, file_transitions)
    suspicious_filenames = {s["filename"] for s in suspicious_entries}

    all_transitions = _exclude_suspicious_files(file_info, suspicious_filenames)
    if not all_transitions:
        raise HTTPException(status_code=400, detail="No valid transitions found in the uploaded files.")

    stats_result = calculateStatistics(all_transitions)
    statistics = stats_result.statistics
    quarantined_entries = stats_result.quarantined

    state_names = {
        name
        for stat in statistics
        for name in (stat.getFromState().getName(), stat.getToState().getName())
    }

    nodes = [NodeSchema(id=name, label=name) for name in sorted(state_names)]

    edge_dicts = [
        {
            "id": f"{stat.getFromState().getName()}-{stat.getToState().getName()}",
            "source": stat.getFromState().getName(),
            "target": stat.getToState().getName(),
            "probability": round(stat.getProbability(), 4),
            "avgSojournTime": round(stat.getSojournAverage(), 2),
            "transitionCount": len(stat.getSojournTimes()),
            "cleanSojournTimes": [float(t) for t in stat.getSojournTimes()],
        }
        for stat in statistics
    ]
    _normalize_probabilities(edge_dicts)
    edges = [EdgeSchema(**d) for d in edge_dicts]

    quarantined = [
        QuarantinedEntrySchema(
            fromState=q.fromState,
            toState=q.toState,
            sojournTime=q.sojournTime,
            outlierScore=round(q.outlierScore, 4),
        )
        for q in quarantined_entries
    ]

    suspicious = [
        SuspiciousFileSchema(
            filename=s["filename"],
            transition=s["transition"],
            fromState=s["fromState"],
            toState=s["toState"],
            count=s["count"],
            avgCount=s["avgCount"],
            allCounts=s.get("allCounts", []),
            transitions=[SuspiciousTransitionEntry(**t) for t in s.get("transitions", [])],
        )
        for s in suspicious_entries
    ]

    return AnalysisResponse(nodes=nodes, edges=edges, quarantined=quarantined, suspiciousFiles=suspicious)
