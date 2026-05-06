import asyncio
import json
import os
import tempfile
import pathlib
from typing import AsyncGenerator, List

import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

from classes.json_file_reading_strategy import JsonFileReadingStrategy
from classes.json_log_parsing_strategy import JsonLogParsingStrategy
from utils.statistics import calculateStatistics
from utils.outlier_detection import detect_outliers_with_scores, detect_suspicious_files
from backend.schemas import AnalysisResponse, NodeSchema, EdgeSchema, QuarantinedEntrySchema, SuspiciousFileSchema

router = APIRouter(prefix="/api", tags=["analysis"])


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _stream_analysis(files: List[UploadFile]) -> AsyncGenerator[str, None]:
    reader = JsonFileReadingStrategy()
    parser = JsonLogParsingStrategy()
    all_transitions = []
    file_counts: dict[str, dict[tuple[str, str], int]] = {}
    num_files = len(files)

    # Phase 1: read files (5 – 30 %)
    for i, upload in enumerate(files):
        yield _sse({"percent": int(5 + i / num_files * 25), "message": f"Reading file {i + 1} of {num_files}…"})
        filename = upload.filename or f"file_{i + 1}"
        content = await upload.read()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            file_wrapper = reader.readFile(pathlib.Path(tmp_path))
            log_file = parser.createLogFile(file_wrapper)
            transitions = log_file.getStateTransitionInfoList()
            all_transitions.extend(transitions)
            counts: dict[tuple[str, str], int] = {}
            for info in transitions:
                key = (info.getFromState().getName(), info.getToState().getName())
                counts[key] = counts.get(key, 0) + 1
            file_counts[filename] = counts
        finally:
            os.unlink(tmp_path)

    if not all_transitions:
        yield _sse({"error": "No valid transitions found in the uploaded files."})
        return

    # Phase 1.5: suspicious file detection (31 %)
    yield _sse({"percent": 31, "message": "Checking file consistency…"})
    suspicious_files = await asyncio.to_thread(detect_suspicious_files, file_counts)

    # Phase 2: group transitions (32 %)
    yield _sse({"percent": 32, "message": "Grouping transitions…"})
    groups: dict[tuple[str, str], list] = {}
    state_objects: dict[str, object] = {}
    for info in all_transitions:
        fn = info.getFromState().getName()
        tn = info.getToState().getName()
        state_objects[fn] = info.getFromState()
        state_objects[tn] = info.getToState()
        key = (fn, tn)
        if key not in groups:
            groups[key] = []
        groups[key].append(info)

    # Phase 3: outlier detection per (from, to) pair (38 – 85 %)
    num_pairs = len(groups)
    quarantined_list: list[dict] = []
    clean_by_pair: dict[tuple[str, str], list] = {}

    for pair_idx, ((fn, tn), entries) in enumerate(groups.items()):
        pct = int(38 + pair_idx / num_pairs * 47)
        yield _sse({"percent": pct, "message": f"Outlier detection: {fn} → {tn}  ({pair_idx + 1}/{num_pairs})"})
        sojourn_times = [info.getSojournTime() for info in entries]
        is_outlier, scores = await asyncio.to_thread(detect_outliers_with_scores, sojourn_times)

        clean = []
        for info, outlier, score in zip(entries, is_outlier, scores):
            if outlier:
                quarantined_list.append({
                    "fromState": fn, "toState": tn,
                    "sojournTime": float(info.getSojournTime()),
                    "outlierScore": round(score, 4),
                })
            else:
                clean.append(info)
        clean_by_pair[(fn, tn)] = clean if clean else list(entries)

    # Phase 4: build statistics & response (86 – 100 %)
    yield _sse({"percent": 86, "message": "Computing statistics…"})
    from_counts: dict[str, int] = {}
    for (fn, _), entries in clean_by_pair.items():
        from_counts[fn] = from_counts.get(fn, 0) + len(entries)

    state_names: set[str] = set()
    edges: list[dict] = []
    for (fn, tn), clean_entries in clean_by_pair.items():
        state_names.add(fn)
        state_names.add(tn)
        sojourn_times = [info.getSojournTime() for info in clean_entries]
        edges.append({
            "id": f"{fn}-{tn}", "source": fn, "target": tn,
            "probability": round(len(clean_entries) / from_counts[fn], 4),
            "avgSojournTime": round(float(np.average(sojourn_times)), 2),
            "transitionCount": len(sojourn_times),
            "cleanSojournTimes": [float(t) for t in sojourn_times],
        })

    yield _sse({"percent": 95, "message": "Building response…"})
    nodes = [{"id": n, "label": n} for n in sorted(state_names)]
    yield _sse({"percent": 100, "message": "Done!", "result": {
        "nodes": nodes, "edges": edges,
        "quarantined": quarantined_list,
        "suspiciousFiles": suspicious_files,
    }})


@router.post("/analyze/stream")
async def analyze_files_stream(files: List[UploadFile] = File(...)):
    return StreamingResponse(
        _stream_analysis(files),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_files(files: List[UploadFile] = File(...)):
    reader = JsonFileReadingStrategy()
    parser = JsonLogParsingStrategy()
    all_transitions = []
    file_counts: dict[str, dict[tuple[str, str], int]] = {}

    for i, upload in enumerate(files):
        filename = upload.filename or f"file_{i + 1}"
        content = await upload.read()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            file_wrapper = reader.readFile(pathlib.Path(tmp_path))
            log_file = parser.createLogFile(file_wrapper)
            transitions = log_file.getStateTransitionInfoList()
            all_transitions.extend(transitions)
            counts: dict[tuple[str, str], int] = {}
            for info in transitions:
                key = (info.getFromState().getName(), info.getToState().getName())
                counts[key] = counts.get(key, 0) + 1
            file_counts[filename] = counts
        finally:
            os.unlink(tmp_path)

    if not all_transitions:
        raise HTTPException(status_code=400, detail="No valid transitions found in the uploaded files.")

    statistics, quarantined_entries = calculateStatistics(all_transitions)
    suspicious_entries = detect_suspicious_files(file_counts)

    state_names: set[str] = set()
    for stat in statistics:
        state_names.add(stat.getFromState().getName())
        state_names.add(stat.getToState().getName())

    nodes = [NodeSchema(id=name, label=name) for name in sorted(state_names)]

    edges = [
        EdgeSchema(
            id=f"{stat.getFromState().getName()}-{stat.getToState().getName()}",
            source=stat.getFromState().getName(),
            target=stat.getToState().getName(),
            probability=round(stat.getProbability(), 4),
            avgSojournTime=round(stat.getSojournAverage(), 2),
            transitionCount=len(stat.getSojournTimes()),
            cleanSojournTimes=[float(t) for t in stat.getSojournTimes()],
        )
        for stat in statistics
    ]

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
            outlierScore=s["outlierScore"],
        )
        for s in suspicious_entries
    ]

    return AnalysisResponse(nodes=nodes, edges=edges, quarantined=quarantined, suspiciousFiles=suspicious)
