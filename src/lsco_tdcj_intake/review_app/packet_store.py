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


def get_packet(packet_id: str) -> dict[str, str] | None:
    """Return one packet registry row by packet_id."""
    packet_id = (packet_id or "").strip()
    for row in read_packet_registry():
        if (row.get("packet_id") or "").strip() == packet_id:
            return row
    return None


def get_packet_dir(packet_id: str) -> Path:
    """Return the processed review packet folder path."""
    return REVIEW_PACKETS_ROOT / packet_id


def read_packet_review_rows(packet_id: str) -> list[dict[str, str]]:
    """Read pending human review rows for one packet."""
    packet_dir = get_packet_dir(packet_id)
    review_csv = packet_dir / "human_review_queue_FOR_REVIEW.csv"

    if not review_csv.exists():
        return []

    with review_csv.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def add_evidence_paths(packet_id: str, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Attach packet-relative evidence image paths when available."""
    packet_dir = get_packet_dir(packet_id)

    enriched_rows: list[dict[str, str]] = []
    for row in rows:
        enriched = dict(row)
        field_id = (row.get("field_id") or "").strip()

        evidence_relative_path = ""

        ocr_evidence_path = packet_dir / "evidence" / "page1_ocr_crops" / f"{field_id}.png"
        if field_id.startswith("p1_") and ocr_evidence_path.exists():
            evidence_relative_path = str(
                ocr_evidence_path.relative_to(packet_dir)
            ).replace("\\", "/")

        if not evidence_relative_path:
            checkbox_evidence_root = packet_dir / "evidence" / "checkbox_debug"
            if checkbox_evidence_root.exists():
                checkbox_matches = list(checkbox_evidence_root.rglob(f"{field_id}.png"))
                if checkbox_matches:
                    evidence_relative_path = str(
                        checkbox_matches[0].relative_to(packet_dir)
                    ).replace("\\", "/")

        enriched["evidence_relative_path"] = evidence_relative_path
        enriched_rows.append(enriched)

    return enriched_rows