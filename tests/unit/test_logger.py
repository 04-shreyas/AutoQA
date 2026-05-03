import logging
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from autoqa.utils.logger import _LOGGER_CACHE, get_logger

@pytest.fixture(autouse=True)
def clear_cache():
    _LOGGER_CACHE.clear()

def test_get_logger_new_agent(clear_cache):
    """Test creating a new logger for an agent."""
    agent_name = "test_agent"
    logger = get_logger(agent_name)
    assert isinstance(logger, logging.Logger)
    assert len(logger.handlers) == 2
    assert logger.level == logging.INFO

def test_get_logger_existing_agent(clear_cache):
    """Test retrieving an existing logger for an agent."""
    agent_name = "existing_agent"
    first_logger = get_logger(agent_name)
    logger = get_logger(agent_name)
    assert logger is first_logger
    assert isinstance(logger, logging.Logger)
    assert len(logger.handlers) == 2
    assert logger.level == logging.INFO

def test_get_logger_log_directory(clear_cache):
    """Test that the log directory is created if it does not exist."""
    agent_name = "test_agent"
    get_logger(agent_name)
    log_dir = Path("logs")
    assert log_dir.exists()
    assert log_dir.is_dir()

def test_get_logger_console_handler(clear_cache):
    """Test that a console handler is added to the logger."""
    agent_name = "test_agent"
    logger = get_logger(agent_name)
    console_handler = next((h for h in logger.handlers if isinstance(h, logging.StreamHandler)), None)
    assert console_handler is not None

def test_get_logger_file_handler(clear_cache):
    """Test that a file handler is added to the logger."""
    agent_name = "test_agent"
    logger = get_logger(agent_name)
    file_handler = next((h for h in logger.handlers if isinstance(h, logging.FileHandler)), None)
    assert file_handler is not None
    file_path = Path(file_handler.baseFilename)
    assert file_path.name == "autoqa.log"
    assert file_path.parent.name == "logs"

def test_get_logger_formatter(clear_cache):
    """Test that the formatter is set correctly on handlers."""
    agent_name = "test_agent"
    logger = get_logger(agent_name)
    for handler in logger.handlers:
        assert isinstance(handler.formatter, logging.Formatter)
        assert handler.formatter._fmt == "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
