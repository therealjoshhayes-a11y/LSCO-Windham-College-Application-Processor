"""Load locked LSCO TDCJ form maps.

The locked JSON maps are the source of truth for field geometry.
Do not modify those JSON files in-place.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lsco_tdcj_intake.paths import get_page1_map_path, get_page2_map_path


@dataclass(frozen=True)
class FormMap:
    """A loaded form map JSON file."""

    path: Path
    document_id: str
    revision: str
    page_number: int
    width: float
    height: float
    dpi: int
    render_rules: dict[str, Any]
    anchors: dict[str, Any]
    locked_zones: list[dict[str, Any]]
    fields: dict[str, dict[str, Any]]
    raw: dict[str, Any]


def load_json(path: Path) -> dict[str, Any]:
    """Load one JSON file."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_form_map(path: Path) -> FormMap:
    """Load and lightly validate one locked form map."""
    raw = load_json(path)

    required_keys = {
        "document_id",
        "revision",
        "page_number",
        "width",
        "height",
        "dpi",
        "render_rules",
        "anchors",
        "locked_zones",
        "fields",
    }
    missing = sorted(required_keys - set(raw))
    if missing:
        raise ValueError(f"{path} is missing required keys: {missing}")

    return FormMap(
        path=path,
        document_id=str(raw["document_id"]),
        revision=str(raw["revision"]),
        page_number=int(raw["page_number"]),
        width=float(raw["width"]),
        height=float(raw["height"]),
        dpi=int(raw["dpi"]),
        render_rules=dict(raw["render_rules"]),
        anchors=dict(raw["anchors"]),
        locked_zones=list(raw["locked_zones"]),
        fields=dict(raw["fields"]),
        raw=raw,
    )


def load_page1_map() -> FormMap:
    """Load the locked Page 1 map."""
    return load_form_map(get_page1_map_path())


def load_page2_map() -> FormMap:
    """Load the locked Page 2 map."""
    return load_form_map(get_page2_map_path())


def load_all_maps() -> dict[int, FormMap]:
    """Load all locked page maps keyed by page number."""
    maps = [load_page1_map(), load_page2_map()]
    return {form_map.page_number: form_map for form_map in maps}


def list_field_ids(form_map: FormMap) -> list[str]:
    """Return field IDs in map order."""
    return list(form_map.fields.keys())