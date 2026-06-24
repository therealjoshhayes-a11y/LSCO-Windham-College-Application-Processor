from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEW_PACKETS_ROOT = PROJECT_ROOT / "data" / "processed" / "review_packets"
REGISTRY_PATH = REVIEW_PACKETS_ROOT / "packet_registry.csv"

DEFAULT_DOCUMENT_TYPE = "tdcj_application_v5_green"
DEFAULT_EXPORT_SCHEMA_VERSION = "headers_xlsx_2026_06"

REGISTRY_COLUMNS = [
    "packet_id",
    "source_tif",
    "document_type",
    "export_schema_version",
    "status",
    "student_last_name",
    "student_first_name",
    "student_mi",
    "tdcj_number",
    "dob",
    "pending_review_count",
    "created_at",
    "updated_at",
    "reviewed_at",
    "approved_at",
    "exported_at",
    "reviewer",
    "approved_pdf_path",
    "admissions_export_path",
    "error",
]


FINAL_STATUSES_TO_PRESERVE = {"approved", "exported"}


@dataclass
class PacketRegistryRow:
    packet_id: str
    source_tif: str = ""
    document_type: str = DEFAULT_DOCUMENT_TYPE
    export_schema_version: str = DEFAULT_EXPORT_SCHEMA_VERSION
    status: str = "review_pending"
    student_last_name: str = ""
    student_first_name: str = ""
    student_mi: str = ""
    tdcj_number: str = ""
    dob: str = ""
    pending_review_count: str = "0"
    created_at: str = ""
    updated_at: str = ""
    reviewed_at: str = ""
    approved_at: str = ""
    exported_at: str = ""
    reviewer: str = ""
    approved_pdf_path: str = ""
    admissions_export_path: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, str]:
        return {column: str(getattr(self, column, "")) for column in REGISTRY_COLUMNS}


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def read_existing_registry() -> dict[str, dict[str, str]]:
    if not REGISTRY_PATH.exists():
        return {}

    with REGISTRY_PATH.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = {}
        for row in reader:
            packet_id = (row.get("packet_id") or "").strip()
            if packet_id:
                rows[packet_id] = {column: row.get(column, "") for column in REGISTRY_COLUMNS}
        return rows


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def first_nonempty(row: dict[str, str], possible_keys: list[str]) -> str:
    for key in possible_keys:
        value = (row.get(key) or "").strip()
        if value:
            return value
    return ""


def get_packet_value(packet_dir: Path, field_id: str) -> str:
    values_csv = packet_dir / "reviewed_packet_values.csv"
    rows = read_csv_rows(values_csv)

    for row in rows:
        row_field_id = (row.get("field_id") or row.get("Field ID") or "").strip()
        if row_field_id == field_id:
            return first_nonempty(
                row,
                [
                    "reviewed_value",
                    "final_value",
                    "value",
                    "machine_value",
                    "ocr_value",
                    "accepted_value",
                ],
            )

    return ""


def get_pending_review_count(packet_dir: Path) -> int:
    review_csv = packet_dir / "human_review_queue_FOR_REVIEW.csv"
    rows = read_csv_rows(review_csv)
    return len(rows)


def infer_source_tif(packet_id: str) -> str:
    tif_path = PROJECT_ROOT / "data" / "incoming" / "scans" / f"{packet_id}.tif"
    tiff_path = PROJECT_ROOT / "data" / "incoming" / "scans" / f"{packet_id}.tiff"

    if tif_path.exists():
        return str(tif_path.relative_to(PROJECT_ROOT))

    if tiff_path.exists():
        return str(tiff_path.relative_to(PROJECT_ROOT))

    return ""


def build_row_for_packet(packet_dir: Path, existing: dict[str, str] | None) -> PacketRegistryRow:
    packet_id = packet_dir.name
    timestamp = now_iso()

    pending_count = get_pending_review_count(packet_dir)

    if pending_count > 0:
        default_status = "review_pending"
    else:
        default_status = "review_in_progress"

    status = default_status

    if existing:
        existing_status = (existing.get("status") or "").strip()
        if existing_status in FINAL_STATUSES_TO_PRESERVE:
            status = existing_status
        elif existing_status == "failed":
            status = "failed"
        elif existing_status == "review_in_progress":
            status = "review_in_progress"

    created_at = existing.get("created_at", "") if existing else ""
    if not created_at:
        created_at = timestamp

    row = PacketRegistryRow(
        packet_id=packet_id,
        source_tif=(existing.get("source_tif") if existing else "") or infer_source_tif(packet_id),
        document_type=(existing.get("document_type") if existing else "") or DEFAULT_DOCUMENT_TYPE,
        export_schema_version=(existing.get("export_schema_version") if existing else "") or DEFAULT_EXPORT_SCHEMA_VERSION,
        status=status,
        student_last_name=get_packet_value(packet_dir, "p1_last_name"),
        student_first_name=get_packet_value(packet_dir, "p1_first_name"),
        student_mi=get_packet_value(packet_dir, "p1_mi"),
        tdcj_number=get_packet_value(packet_dir, "p1_tdcj_number"),
        dob=get_packet_value(packet_dir, "p1_date_of_birth"),
        pending_review_count=str(pending_count),
        created_at=created_at,
        updated_at=timestamp,
        reviewed_at=existing.get("reviewed_at", "") if existing else "",
        approved_at=existing.get("approved_at", "") if existing else "",
        exported_at=existing.get("exported_at", "") if existing else "",
        reviewer=existing.get("reviewer", "") if existing else "",
        approved_pdf_path=existing.get("approved_pdf_path", "") if existing else "",
        admissions_export_path=existing.get("admissions_export_path", "") if existing else "",
        error=existing.get("error", "") if existing else "",
    )

    return row


def find_packet_dirs() -> list[Path]:
    if not REVIEW_PACKETS_ROOT.exists():
        return []

    packet_dirs = []
    for child in REVIEW_PACKETS_ROOT.iterdir():
        if not child.is_dir():
            continue
        if child.name.startswith("."):
            continue
        packet_dirs.append(child)

    return sorted(packet_dirs, key=lambda p: p.name.lower())


def write_registry(rows: list[PacketRegistryRow]) -> None:
    REVIEW_PACKETS_ROOT.mkdir(parents=True, exist_ok=True)

    with REGISTRY_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REGISTRY_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())


def main() -> None:
    existing_registry = read_existing_registry()
    packet_dirs = find_packet_dirs()

    rows = []
    for packet_dir in packet_dirs:
        existing = existing_registry.get(packet_dir.name)
        rows.append(build_row_for_packet(packet_dir, existing))

    write_registry(rows)

    print(f"Packet folders found: {len(packet_dirs)}")
    print(f"Registry written: {REGISTRY_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()