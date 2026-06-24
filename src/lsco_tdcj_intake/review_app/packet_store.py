from __future__ import annotations

import csv
import subprocess
import sys
from datetime import datetime
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
    """Read packet registry rows."""
    if not REGISTRY_PATH.exists():
        return []

    with REGISTRY_PATH.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def filter_packets(
    packets: list[dict[str, str]],
    status_filter: str,
) -> list[dict[str, str]]:
    """Filter packets for dashboard display."""
    status_filter = (status_filter or "active").strip().lower()

    if status_filter == "all":
        return packets

    if status_filter == "active":
        return [
            packet for packet in packets
            if (packet.get("status") or "").strip() in DEFAULT_VISIBLE_STATUSES
        ]

    return [
        packet for packet in packets
        if (packet.get("status") or "").strip() == status_filter
    ]


def registry_summary(packets: list[dict[str, str]]) -> dict[str, int]:
    """Summarize packet counts by status."""
    summary = {
        "total": len(packets),
        "review_pending": 0,
        "review_in_progress": 0,
        "approved": 0,
        "exported": 0,
        "failed": 0,
    }

    for packet in packets:
        status = (packet.get("status") or "").strip()
        if status in summary:
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
    """Read human review rows for one packet."""
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


def save_review_decision(
    packet_id: str,
    field_id: str,
    action: str,
    review_value: str,
    review_notes: str,
) -> bool:
    """Save one human review decision back to the reviewer CSV."""
    packet_dir = get_packet_dir(packet_id)
    review_csv = packet_dir / "human_review_queue_FOR_REVIEW.csv"

    if not review_csv.exists():
        return False

    with review_csv.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    updated = False
    for row in rows:
        if (row.get("field_id") or "").strip() != field_id:
            continue

        machine_value = row.get("machine_value") or ""

        if action == "accept_machine":
            row["review_value"] = machine_value
            row["status"] = "accepted_by_reviewer"
        elif action == "save_correction":
            row["review_value"] = review_value.strip()
            row["status"] = "corrected_by_reviewer"
        elif action == "needs_supervisor":
            row["review_value"] = review_value.strip()
            row["status"] = "needs_supervisor_review"
        else:
            return False

        row["review_notes"] = review_notes.strip()
        updated = True
        break

    if not updated:
        return False

    with review_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return True


def packet_has_unresolved_reviews(packet_id: str) -> bool:
    """Return True when a packet still has review rows without final decisions."""
    packet_dir = get_packet_dir(packet_id)
    review_csv = packet_dir / "human_review_queue_FOR_REVIEW.csv"

    if not review_csv.exists():
        return True

    final_statuses = {
        "accepted_by_reviewer",
        "corrected_by_reviewer",
    }

    with review_csv.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        status = (row.get("status") or "").strip()
        if status not in final_statuses:
            return True

    return False


def rebuild_final_packet_outputs(packet_id: str) -> bool:
    """Rebuild reviewed packet outputs and admissions export from reviewer decisions."""
    packet_dir = get_packet_dir(packet_id)

    human_review_csv = packet_dir / "human_review_queue_FOR_REVIEW.csv"
    machine_accepted_csv = packet_dir / "page1_machine_accepted.csv"
    checkbox_summary_csv = packet_dir / "checkbox_review_summary.csv"
    reviewed_packet_json = packet_dir / "reviewed_packet.json"
    reviewed_packet_values_csv = packet_dir / "reviewed_packet_values.csv"
    admissions_export_row_csv = packet_dir / "admissions_export_row.csv"

    required_inputs = [
        human_review_csv,
        machine_accepted_csv,
        checkbox_summary_csv,
    ]

    if any(not path.exists() for path in required_inputs):
        return False

    build_reviewed_cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "build_reviewed_packet.py"),
        "--packet-id",
        packet_id,
        "--human-review-csv",
        str(human_review_csv),
        "--machine-accepted-csv",
        str(machine_accepted_csv),
        "--checkbox-summary-csv",
        str(checkbox_summary_csv),
        "--output-json",
        str(reviewed_packet_json),
        "--output-csv",
        str(reviewed_packet_values_csv),
    ]

    export_admissions_cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "export_admissions_row.py"),
        "--reviewed-packet-json",
        str(reviewed_packet_json),
        "--output-csv",
        str(admissions_export_row_csv),
    ]

    try:
        subprocess.run(build_reviewed_cmd, cwd=PROJECT_ROOT, check=True)
        subprocess.run(export_admissions_cmd, cwd=PROJECT_ROOT, check=True)
    except subprocess.CalledProcessError:
        return False

    return True


def approve_packet(packet_id: str, reviewer: str = "local_app") -> bool:
    """Rebuild final outputs and mark one packet approved in the packet registry."""
    if packet_has_unresolved_reviews(packet_id):
        return False

    if not rebuild_final_packet_outputs(packet_id):
        return False

    if not REGISTRY_PATH.exists():
        return False

    with REGISTRY_PATH.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    updated = False
    now = datetime.now().isoformat(timespec="seconds")

    for row in rows:
        if (row.get("packet_id") or "").strip() != packet_id:
            continue

        row["status"] = "approved"
        row["reviewed_at"] = row.get("reviewed_at") or now
        row["approved_at"] = now
        row["updated_at"] = now
        row["reviewer"] = reviewer
        row["error"] = ""
        updated = True
        break

    if not updated:
        return False

    with REGISTRY_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return True