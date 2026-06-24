from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEW_PACKETS_ROOT = PROJECT_ROOT / "data" / "processed" / "review_packets"
REGISTRY_PATH = REVIEW_PACKETS_ROOT / "packet_registry.csv"
EXPORT_ROOT = PROJECT_ROOT / "data" / "exports" / "admissions"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    if not REGISTRY_PATH.exists():
        print(f"Missing registry: {REGISTRY_PATH}")
        return 1

    registry_rows = read_csv_rows(REGISTRY_PATH)
    approved_packets = [
        row for row in registry_rows
        if (row.get("status") or "").strip() == "approved"
    ]

    export_rows: list[dict[str, str]] = []
    missing_exports: list[str] = []

    for packet in approved_packets:
        packet_id = (packet.get("packet_id") or "").strip()
        packet_dir = REVIEW_PACKETS_ROOT / packet_id
        export_path = packet_dir / "admissions_export_row.csv"

        if not export_path.exists():
            missing_exports.append(packet_id)
            continue

        packet_export_rows = read_csv_rows(export_path)
        for row in packet_export_rows:
            row["Packet ID"] = packet_id
            export_rows.append(row)

    if not export_rows:
        print("No approved admissions export rows found.")
        if missing_exports:
            print(f"Approved packets missing export rows: {missing_exports}")
        return 1

    original_fieldnames = list(export_rows[0].keys())
    fieldnames = ["Packet ID"] + [
        name for name in original_fieldnames
        if name != "Packet ID"
    ]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = EXPORT_ROOT / f"approved_admissions_batch_{timestamp}.csv"

    write_csv_rows(output_path, export_rows, fieldnames)

    print(f"Approved packets found: {len(approved_packets)}")
    print(f"Admissions rows exported: {len(export_rows)}")
    print(f"Output CSV: {output_path}")

    if missing_exports:
        print(f"Approved packets missing export rows: {missing_exports}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
