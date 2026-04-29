import os
import tempfile
import pathlib
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException

from classes.json_file_reading_strategy import JsonFileReadingStrategy
from classes.json_log_parsing_strategy import JsonLogParsingStrategy
from utils.statistics import calculateStatistics
from backend.schemas import AnalysisResponse, NodeSchema, EdgeSchema

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_files(files: List[UploadFile] = File(...)):
    reader = JsonFileReadingStrategy()
    parser = JsonLogParsingStrategy()
    all_transitions = []

    for upload in files:
        content = await upload.read()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            file_wrapper = reader.readFile(pathlib.Path(tmp_path))
            log_file = parser.createLogFile(file_wrapper)
            all_transitions.extend(log_file.getStateTransitionInfoList())
        finally:
            os.unlink(tmp_path)

    if not all_transitions:
        raise HTTPException(status_code=400, detail="No valid transitions found in the uploaded files.")

    statistics = calculateStatistics(all_transitions)

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
        )
        for stat in statistics
    ]

    return AnalysisResponse(nodes=nodes, edges=edges)
