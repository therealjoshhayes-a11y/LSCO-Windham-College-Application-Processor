from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REVIEW_PACKETS_ROOT = PROJECT_ROOT / "data" / "processed" / "review_packets"
REGISTRY_PATH = REVIEW_PACKETS_ROOT / "packet_registry.csv"

DEFAULT_VISIBLE_STATUSES = {
    "review_pending",
    "review_in_progress",
    "failed",
}


def read_packet_registry() -> list[dict[str, str]]:
    """Read packet registry rows for the review dashboard."""
    if not REGISTRY_PATH.exists():
        return []

    with REGISTRY_PATH.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    return sorted(rows, key=lambda row: row.get("packet_id", "").lower())


def filter_packets(rows: list[dict[str, str]], status_filter: str = "active") -> list[dict[str, str]]:
    """Filter packets for dashboard display."""
    status_filter = (status_filter or "active").strip().lower()

    if status_filter == "all":
        return rows

    if status_filter == "active":
        return [
            row for row in rows
            if (row.get("status") or "").strip().lower() in DEFAULT_VISIBLE_STATUSES
        ]

    return [
        row for row in rows
        if (row.get("status") or "").strip().lower() == status_filter
    ]


def registry_summary(rows: list[dict[str, str]]) -> dict[str, int]:
    """Count packets by status."""
    summary: dict[str, int] = {
        "total": len(rows),
        "review_pending": 0,
        "review_in_progress": 0,
        "approved": 0,
        "exported": 0,
        "failed": 0,
    }

    for row in rows:
        status = (row.get("status") or "").strip().lower()
        if status not in summary:
            summary[status] = 0
        summary[status] += 1

    return summary