from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PACKET_ID = "image-1"

DEFAULT_REVIEW_PACKET_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "review_packets"
    / DEFAULT_PACKET_ID
)

DEFAULT_HUMAN_REVIEW_CSV = DEFAULT_REVIEW_PACKET_DIR / "human_review_queue.csv"
DEFAULT_MACHINE_ACCEPTED_CSV = DEFAULT_REVIEW_PACKET_DIR / "page1_machine_accepted.csv"
DEFAULT_CHECKBOX_SUMMARY_CSV = DEFAULT_REVIEW_PACKET_DIR / "checkbox_review_summary.csv"
DEFAULT_REVIEWED_PACKET_JSON = DEFAULT_REVIEW_PACKET_DIR / "reviewed_packet.json"
DEFAULT_REVIEWED_PACKET_VALUES_CSV = DEFAULT_REVIEW_PACKET_DIR / "reviewed_packet_values.csv"
DEFAULT_ADMISSIONS_EXPORT_ROW_CSV = DEFAULT_REVIEW_PACKET_DIR / "admissions_export_row.csv"


def run_step(label: str, command: list[str]) -> None:
    print()
    print(f"=== {label} ===")
    print(" ".join(command))

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Step failed: {label}")


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Apply reviewer-entered review_value fields by rebuilding "
            "reviewed_packet.json, reviewed_packet_values.csv, and admissions_export_row.csv."
        )
    )

    parser.add_argument(
        "--packet-id",
        default=DEFAULT_PACKET_ID,
        help="Packet id.",
    )

    parser.add_argument(
        "--human-review-csv",
        default=str(DEFAULT_HUMAN_REVIEW_CSV),
        help="Input human_review_queue.csv with reviewer-entered review_value values.",
    )

    parser.add_argument(
        "--machine-accepted-csv",
        default=str(DEFAULT_MACHINE_ACCEPTED_CSV),
        help="Input page1_machine_accepted.csv.",
    )

    parser.add_argument(
        "--checkbox-summary-csv",
        default=str(DEFAULT_CHECKBOX_SUMMARY_CSV),
        help="Input checkbox_review_summary.csv.",
    )

    parser.add_argument(
        "--reviewed-packet-json",
        default=str(DEFAULT_REVIEWED_PACKET_JSON),
        help="Output reviewed_packet.json.",
    )

    parser.add_argument(
        "--reviewed-packet-values-csv",
        default=str(DEFAULT_REVIEWED_PACKET_VALUES_CSV),
        help="Output reviewed_packet_values.csv.",
    )

    parser.add_argument(
        "--admissions-export-row-csv",
        default=str(DEFAULT_ADMISSIONS_EXPORT_ROW_CSV),
        help="Output admissions_export_row.csv.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    packet_id = str(args.packet_id)

    human_review_csv = Path(args.human_review_csv).resolve()
    machine_accepted_csv = Path(args.machine_accepted_csv).resolve()
    checkbox_summary_csv = Path(args.checkbox_summary_csv).resolve()
    reviewed_packet_json = Path(args.reviewed_packet_json).resolve()
    reviewed_packet_values_csv = Path(args.reviewed_packet_values_csv).resolve()
    admissions_export_row_csv = Path(args.admissions_export_row_csv).resolve()

    require_file(human_review_csv, "Human review CSV")
    require_file(machine_accepted_csv, "Machine accepted CSV")
    require_file(checkbox_summary_csv, "Checkbox summary CSV")

    run_step(
        "Build reviewed packet values",
        [
            sys.executable,
            "scripts/build_reviewed_packet.py",
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
        ],
    )

    run_step(
        "Export draft admissions row",
        [
            sys.executable,
            "scripts/export_admissions_row.py",
            "--reviewed-packet-json",
            str(reviewed_packet_json),
            "--output-csv",
            str(admissions_export_row_csv),
        ],
    )

    print()
    print("=== Review values applied ===")
    print(f"Packet id: {packet_id}")
    print(f"Human review CSV: {human_review_csv}")
    print(f"Reviewed packet JSON: {reviewed_packet_json}")
    print(f"Reviewed packet values CSV: {reviewed_packet_values_csv}")
    print(f"Admissions export row CSV: {admissions_export_row_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())