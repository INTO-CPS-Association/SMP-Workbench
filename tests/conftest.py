import json
import pytest
from pathlib import Path

from classes.standard_state import StandardState
from classes.standard_state_transition_info import StandardStateTransitionInfo
from classes.json_file_reading_strategy import JsonFileReadingStrategy
from classes.json_log_parsing_strategy import JsonLogParsingStrategy

# ---------------------------------------------------------------------------
# File path constants — updated to match current test-file layout
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
NORMAL_FILE = REPO_ROOT / "files" / "test_files" / "normal" / "tf0" / "test_file_0_1000.json"
NORMAL_FILE_2 = REPO_ROOT / "files" / "test_files" / "normal" / "tf1" / "test_file_1_1000.json"
OUTLIER_FILE = REPO_ROOT / "files" / "test_files" / "outlier" / "tf0" / "test_file_0_1000.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_state(name: str) -> StandardState:
    return StandardState(name)


def make_transition(fn: str, tn: str, sojourn: int) -> StandardStateTransitionInfo:
    return StandardStateTransitionInfo(make_state(fn), make_state(tn), sojourn)


def make_transitions(triples: list) -> list:
    return [make_transition(fn, tn, t) for fn, tn, t in triples]


def load_transitions(path: Path) -> list:
    reader = JsonFileReadingStrategy()
    parser = JsonLogParsingStrategy()
    return parser.createLogFile(reader.readFile(path)).getStateTransitionInfoList()


# ---------------------------------------------------------------------------
# Session-scoped file fixtures (read real files once per session)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def normal_file_path():
    return NORMAL_FILE


@pytest.fixture(scope="session")
def normal_file_path_2():
    return NORMAL_FILE_2


@pytest.fixture(scope="session")
def outlier_file_path():
    return OUTLIER_FILE


@pytest.fixture(scope="session")
def normal_transitions():
    return load_transitions(NORMAL_FILE)


@pytest.fixture(scope="session")
def normal_transitions_2():
    return load_transitions(NORMAL_FILE_2)


@pytest.fixture(scope="session")
def outlier_transitions():
    return load_transitions(OUTLIER_FILE)


# ---------------------------------------------------------------------------
# Function-scoped in-memory fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_transitions():
    """10 A→B and 10 B→A transitions — enough for statistics and outlier detection."""
    data = (
        [("A", "B", 10 + i) for i in range(10)] +
        [("B", "A", 20 + i) for i in range(10)]
    )
    return make_transitions(data)


@pytest.fixture
def single_pair_transitions():
    """5 A→B transitions only."""
    return make_transitions([("A", "B", 10 + i) for i in range(5)])


# ---------------------------------------------------------------------------
# Temp-file fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_json_file(tmp_path):
    """A valid .json file (JSONL) with 4 transitions."""
    lines = [
        {"from_state": "A", "to_state": "B", "sojourn_sec": 10},
        {"from_state": "B", "to_state": "A", "sojourn_sec": 20},
        {"from_state": "A", "to_state": "B", "sojourn_sec": 15},
        {"from_state": "B", "to_state": "A", "sojourn_sec": 25},
    ]
    p = tmp_path / "test.json"
    p.write_text("\n".join(json.dumps(obj) for obj in lines))
    return p


@pytest.fixture
def tmp_json_file_with_noise(tmp_path):
    """A .json file with non-JSON lines mixed in (simulates real logger output)."""
    p = tmp_path / "test.json"
    p.write_text(
        "The logger is now ready\n"
        '{"from_state": "A", "to_state": "B", "sojourn_sec": 10}\n'
        "some random text\n"
        '{"from_state": "B", "to_state": "A", "sojourn_sec": 20}\n'
    )
    return p


@pytest.fixture
def tmp_empty_json_file(tmp_path):
    """An empty .json file."""
    p = tmp_path / "empty.json"
    p.write_text("")
    return p


@pytest.fixture
def tmp_non_json_file(tmp_path):
    """A file with a .txt extension — should trigger OSError in the reader."""
    p = tmp_path / "test.txt"
    p.write_text("hello")
    return p
