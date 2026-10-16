"""Configuration constants for MapMind project.

All paths are resolved relative to the project root using ``pathlib.Path``.
"""

from pathlib import Path

# Project root – assume this file resides in <project_root>/utils/config.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Data directories
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
ANNOTATIONS_DIR = PROJECT_ROOT / "data" / "annotations"

# Ensure directories exist at import time
for _dir in (RAW_DATA_DIR, PROCESSED_DATA_DIR, ANNOTATIONS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# Default image dimensions for resizing (width, height)
DEFAULT_MAX_DIMENSION = 1024  # longest side will be resized to this value


def load_env(env_path: Path = PROJECT_ROOT / ".env") -> None:
    """Load environment variables from .env file if it exists."""
    import os
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = val


# Load .env at import time
load_env()

