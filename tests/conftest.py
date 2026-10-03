import hashlib
import warnings
from pathlib import Path

import pytest

from flight_recorder.samples import make_sample_db

# LangGraph warns when its own serializer meets the sample's pydantic model; that is the fork path's
# normal behavior and not what these tests check.
warnings.filterwarnings("ignore", message="Deserializing unregistered type")


@pytest.fixture
def sample_db(tmp_path: Path) -> Path:
    return make_sample_db(tmp_path / "src" / "checkpoints.sqlite")


def dir_fingerprint(folder: Path) -> dict[str, str]:
    """SHA-256 of every file in `folder`; the key set doubles as the file list."""
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir()) if p.is_file()}
