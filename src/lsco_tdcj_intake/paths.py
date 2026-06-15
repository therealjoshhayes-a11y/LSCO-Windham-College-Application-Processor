"""Path helpers for the LSCO TDCJ intake project."""

from pathlib import Path


FORM_ID = "LSCO_TDCJ_Application_v5_green"


def get_project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parents[2]


def get_config_dir() -> Path:
    """Return the config directory."""
    return get_project_root() / "config"


def get_forms_dir() -> Path:
    """Return the forms directory."""
    return get_project_root() / "forms"


def get_form_dir() -> Path:
    """Return the canonical LSCO TDCJ form directory."""
    return get_forms_dir() / FORM_ID


def get_source_pdf_path() -> Path:
    """Return the expected blank source PDF path."""
    return get_form_dir() / "source" / "LSCO_TDCJ_Application_v5_green.pdf"


def get_maps_locked_dir() -> Path:
    """Return the locked maps directory."""
    return get_form_dir() / "maps_locked"


def get_page1_map_path() -> Path:
    """Return the locked Page 1 JSON map path."""
    return get_maps_locked_dir() / "LSCO_TDCJ_Page1_JSON_FINAL.json"


def get_page2_map_path() -> Path:
    """Return the locked Page 2 JSON map path."""
    return get_maps_locked_dir() / "LSCO_TDCJ_Page2_JSON_FINAL.json"


def get_archive_manifest_path() -> Path:
    """Return the locked JSON archive manifest path."""
    return get_maps_locked_dir() / "LSCO_TDCJ_JSON_ARCHIVE_MANIFEST.md"


def get_export_template_path() -> Path:
    """Return the admissions Headers.xlsx path."""
    return get_form_dir() / "export_templates" / "Headers.xlsx"


def get_data_dir() -> Path:
    """Return the data directory."""
    return get_project_root() / "data"


def get_working_dir() -> Path:
    """Return the working data directory."""
    return get_data_dir() / "working"


def get_packet_working_dir(packet_id: str) -> Path:
    """Return the working directory for one packet."""
    return get_working_dir() / "packets" / packet_id


def get_archive_dir() -> Path:
    """Return the archive directory."""
    return get_data_dir() / "archive"


def path_exists(path: Path) -> bool:
    """Return whether a path exists."""
    return path.exists()