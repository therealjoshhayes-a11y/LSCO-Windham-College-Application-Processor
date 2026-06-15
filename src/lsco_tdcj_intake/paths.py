"""Path helpers for the LSCO TDCJ intake project."""
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_forms_dir() -> Path:
    return get_project_root() / "forms"


def get_data_dir() -> Path:
    return get_project_root() / "data"
