from pydantic import BaseModel
from typing import List, Optional


class NodeSchema(BaseModel):
    id: str
    label: str


class DistributionFitSchema(BaseModel):
    distribution: str
    pValue: float
    ksStat: float


class EdgeSchema(BaseModel):
    id: str
    source: str
    target: str
    probability: float
    avgSojournTime: float
    transitionCount: int
    cleanSojournTimes: List[float]
    distributionFit: Optional[DistributionFitSchema] = None


class QuarantinedEntrySchema(BaseModel):
    fromState: str
    toState: str
    sojournTime: float
    outlierScore: float


class SuspiciousTransitionEntry(BaseModel):
    fromState: str
    toState: str
    sojournTime: float
    outlierScore: float = 0.0
    isOutlier: bool = False


class SuspiciousFileSchema(BaseModel):
    filename: str
    transition: str
    fromState: str
    toState: str
    count: int
    avgCount: float
    allCounts: List[int] = []
    allFilenames: List[str] = []
    transitions: List[SuspiciousTransitionEntry] = []


class AnalysisResponse(BaseModel):
    nodes: List[NodeSchema]
    edges: List[EdgeSchema]
    quarantined: List[QuarantinedEntrySchema]
    suspiciousFiles: List[SuspiciousFileSchema] = []


class SojournOutliersRequest(BaseModel):
    transitions: List[SuspiciousTransitionEntry]
    method: str = 'lof'   # 'lof' | 'iqr'
