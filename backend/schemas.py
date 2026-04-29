from pydantic import BaseModel
from typing import List


class NodeSchema(BaseModel):
    id: str
    label: str


class EdgeSchema(BaseModel):
    id: str
    source: str
    target: str
    probability: float
    avgSojournTime: float
    transitionCount: int


class AnalysisResponse(BaseModel):
    nodes: List[NodeSchema]
    edges: List[EdgeSchema]
