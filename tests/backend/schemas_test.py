import pytest
from pydantic import ValidationError

from backend.schemas import (
    NodeSchema,
    DistributionFitSchema,
    EdgeSchema,
    QuarantinedEntrySchema,
    SuspiciousTransitionEntry,
    SuspiciousFileSchema,
    AnalysisResponse,
    SojournOutliersRequest,
)


# ---------------------------------------------------------------------------
# NodeSchema
# ---------------------------------------------------------------------------

class TestNodeSchema:
    def test_valid_construction(self):
        node = NodeSchema(id="A", label="State A")
        assert node.id == "A"
        assert node.label == "State A"

    def test_id_and_label_can_be_same(self):
        node = NodeSchema(id="X", label="X")
        assert node.id == node.label

    def test_missing_id_raises(self):
        with pytest.raises(ValidationError):
            NodeSchema(label="A")  # type: ignore[call-arg]

    def test_missing_label_raises(self):
        with pytest.raises(ValidationError):
            NodeSchema(id="A")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# DistributionFitSchema
# ---------------------------------------------------------------------------

class TestDistributionFitSchema:
    def test_valid_construction(self):
        d = DistributionFitSchema(distribution="Normal", pValue=0.95, ksStat=0.05)
        assert d.distribution == "Normal"
        assert d.pValue == pytest.approx(0.95)
        assert d.ksStat == pytest.approx(0.05)

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            DistributionFitSchema(distribution="Normal", pValue=0.5)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# EdgeSchema
# ---------------------------------------------------------------------------

class TestEdgeSchema:
    @pytest.fixture
    def valid_edge(self):
        return EdgeSchema(
            id="A-B",
            source="A",
            target="B",
            probability=0.75,
            avgSojournTime=30.5,
            transitionCount=10,
            cleanSojournTimes=[10.0, 20.0, 30.0],
        )

    def test_valid_construction(self, valid_edge):
        assert valid_edge.id == "A-B"
        assert valid_edge.source == "A"
        assert valid_edge.target == "B"

    def test_distribution_fit_defaults_to_none(self, valid_edge):
        assert valid_edge.distributionFit is None

    def test_distribution_fit_can_be_set(self):
        edge = EdgeSchema(
            id="A-B",
            source="A",
            target="B",
            probability=0.5,
            avgSojournTime=10.0,
            transitionCount=5,
            cleanSojournTimes=[],
            distributionFit=DistributionFitSchema(distribution="Gamma", pValue=0.8, ksStat=0.1),
        )
        assert edge.distributionFit is not None
        assert edge.distributionFit.distribution == "Gamma"

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            EdgeSchema(source="A", target="B", probability=0.5)  # type: ignore[call-arg]

    def test_clean_sojourn_times_can_be_empty(self):
        edge = EdgeSchema(
            id="A-B", source="A", target="B",
            probability=1.0, avgSojournTime=0.0,
            transitionCount=0, cleanSojournTimes=[],
        )
        assert edge.cleanSojournTimes == []


# ---------------------------------------------------------------------------
# QuarantinedEntrySchema
# ---------------------------------------------------------------------------

class TestQuarantinedEntrySchema:
    def test_valid_construction(self):
        q = QuarantinedEntrySchema(
            fromState="A", toState="B", sojournTime=500.0, outlierScore=0.95
        )
        assert q.fromState == "A"
        assert q.toState == "B"
        assert q.sojournTime == pytest.approx(500.0)
        assert q.outlierScore == pytest.approx(0.95)

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            QuarantinedEntrySchema(fromState="A", toState="B", sojournTime=10.0)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# SuspiciousTransitionEntry
# ---------------------------------------------------------------------------

class TestSuspiciousTransitionEntry:
    def test_defaults_for_optional_fields(self):
        entry = SuspiciousTransitionEntry(fromState="A", toState="B", sojournTime=15.0)
        assert entry.outlierScore == 0.0
        assert entry.isOutlier is False

    def test_explicit_values_stored(self):
        entry = SuspiciousTransitionEntry(
            fromState="X", toState="Y", sojournTime=99.0,
            outlierScore=0.9, isOutlier=True
        )
        assert entry.outlierScore == pytest.approx(0.9)
        assert entry.isOutlier is True

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            SuspiciousTransitionEntry(fromState="A", toState="B")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# SuspiciousFileSchema
# ---------------------------------------------------------------------------

class TestSuspiciousFileSchema:
    def test_valid_minimal_construction(self):
        sf = SuspiciousFileSchema(
            filename="file.json",
            transition="A → B",
            fromState="A",
            toState="B",
            count=50,
            avgCount=10.0,
        )
        assert sf.filename == "file.json"
        assert sf.count == 50

    def test_optional_lists_default_to_empty(self):
        sf = SuspiciousFileSchema(
            filename="f.json", transition="A → B",
            fromState="A", toState="B",
            count=5, avgCount=2.0,
        )
        assert sf.allCounts == []
        assert sf.allFilenames == []
        assert sf.transitions == []

    def test_transitions_accepts_list_of_entries(self):
        entry = SuspiciousTransitionEntry(fromState="A", toState="B", sojournTime=10.0)
        sf = SuspiciousFileSchema(
            filename="f.json", transition="A → B",
            fromState="A", toState="B",
            count=1, avgCount=1.0,
            transitions=[entry],
        )
        assert len(sf.transitions) == 1


# ---------------------------------------------------------------------------
# AnalysisResponse
# ---------------------------------------------------------------------------

class TestAnalysisResponse:
    @pytest.fixture
    def minimal_response(self):
        return AnalysisResponse(
            nodes=[NodeSchema(id="A", label="A")],
            edges=[
                EdgeSchema(
                    id="A-A", source="A", target="A",
                    probability=1.0, avgSojournTime=10.0,
                    transitionCount=1, cleanSojournTimes=[10.0],
                )
            ],
            quarantined=[],
        )

    def test_valid_construction(self, minimal_response):
        assert len(minimal_response.nodes) == 1
        assert len(minimal_response.edges) == 1
        assert minimal_response.quarantined == []

    def test_suspicious_files_defaults_to_empty(self, minimal_response):
        assert minimal_response.suspiciousFiles == []

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            AnalysisResponse(nodes=[], quarantined=[])  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# SojournOutliersRequest
# ---------------------------------------------------------------------------

class TestSojournOutliersRequest:
    def test_valid_construction(self):
        req = SojournOutliersRequest(
            transitions=[
                SuspiciousTransitionEntry(fromState="A", toState="B", sojournTime=10.0)
            ]
        )
        assert len(req.transitions) == 1

    def test_default_method_is_lof(self):
        req = SojournOutliersRequest(transitions=[])
        assert req.method == "lof"

    def test_explicit_method_stored(self):
        req = SojournOutliersRequest(transitions=[], method="iqr")
        assert req.method == "iqr"

    def test_empty_transitions_list_is_valid(self):
        req = SojournOutliersRequest(transitions=[])
        assert req.transitions == []

    def test_missing_transitions_raises(self):
        with pytest.raises(ValidationError):
            SojournOutliersRequest()  # type: ignore[call-arg]
