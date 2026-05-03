from __future__ import annotations

import logging
from pathlib import Path


_LOGGER_CACHE: dict[str, logging.Logger] = {}


def get_logger(agent_name: str) -> logging.Logger:
    if agent_name in _LOGGER_CACHE:
        return _LOGGER_CACHE[agent_name]

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(agent_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        file_handler = logging.FileHandler(log_dir / "autoqa.log")
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    _LOGGER_CACHE[agent_name] = logger
    return logger
