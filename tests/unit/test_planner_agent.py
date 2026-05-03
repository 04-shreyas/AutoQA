import json
from pathlib import Path
from typing import Any

import pytest


def _load_latest_analysis(data_dir: Path) -> dict[str, Any] | None:
    if not data_dir.exists():
        return None

    analysis_files = sorted(data_dir.glob("analysis_*.json"), key=lambda p: p.stat().st_mtime)
    if not analysis_files:
        return None

    try:
        return json.loads(analysis_files[-1].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


@pytest.fixture
def data_dir(tmp_path):
    return tmp_path


@pytest.fixture
def empty_data_dir(tmp_path):
    return tmp_path


@pytest.fixture
def non_existent_data_dir():
    return Path("__missing_dir__")


@pytest.fixture
def analysis_file(data_dir):
    file = data_dir / "analysis_test.json"
    file.write_text(json.dumps({"key": "value"}))
    return file


def test_load_latest_analysis_with_empty_directory(empty_data_dir):
    """Test loading latest analysis with an empty directory."""
    result = _load_latest_analysis(empty_data_dir)
    assert result is None


def test_load_latest_analysis_with_non_existent_directory(non_existent_data_dir):
    """Test loading latest analysis with a non-existent directory."""
    result = _load_latest_analysis(non_existent_data_dir)
    assert result is None


def test_load_latest_analysis_with_single_file(data_dir, analysis_file):
    """Test loading latest analysis with a single analysis file."""
    result = _load_latest_analysis(data_dir)
    assert result == {"key": "value"}


def test_load_latest_analysis_with_multiple_files(data_dir, analysis_file):
    """Test loading latest analysis with multiple analysis files."""
    import time
    old_file = data_dir / "analysis_old.json"
    old_file.write_text(json.dumps({"old_key": "old_value"}))
    time.sleep(0.01)  # Ensure different modification times
    analysis_file.write_text(json.dumps({"key": "value"}))
    result = _load_latest_analysis(data_dir)
    assert result == {"key": "value"}


def test_load_latest_analysis_with_corrupted_file(data_dir, analysis_file):
    """Test loading latest analysis when the most recent file is corrupted."""
    import time
    time.sleep(0.01)  # Ensure different modification times
    corrupted_file = analysis_file.parent / "analysis_corrupted.json"
    corrupted_file.write_text("invalid json")
    result = _load_latest_analysis(data_dir)
    assert result is None  # Most recent file is corrupted