from __future__ import annotations

import argparse
import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PAGE1_OCR_CSV = (
    PROJECT_ROOT
    / "data"
    / "working"
    / "ocr_debug"
    / "page1_ocr"
    / "page1_ocr.csv"
)

DEFAULT_OUTPUT_CSV = (
    PROJECT_ROOT
    / "data"
    / "working"
    / "ocr_debug"
    / "page1_ocr"
    / "page1_machine_accepted.csv"
)

ACCEPTED_STATUSES = {
    "accepted",
    "blank_accepted",
}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Required CSV not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def first_present(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = row.get(name, "")
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def build_accepted_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "field_id": row.get("field_id", ""),
        "status": row.get("status", ""),
        "normalized_text": first_present(
            row,
            ["normalized_text", "normalized", "value"],
        ),
        "raw_text": first_present(row, ["raw_text", "text", "ocr_text"]),
        "normalization": row.get("normalization", ""),
        "confidence": row.get("confidence", ""),
        "notes": row.get("notes", ""),
        "crop_path": first_present(row, ["crop_path", "image_path", "crop"]),
    }


def write_machine_accepted(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "field_id",
        "status",
        "normalized_text",
        "raw_text",
        "normalization",
        "confidence",
        "notes",
        "crop_path",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Page 1 OCR machine-accepted fields."
    )

    parser.add_argument(
        "--ocr-csv",
        default=str(DEFAULT_PAGE1_OCR_CSV),
        help="Input Page 1 OCR CSV.",
    )

    parser.add_argument(
        "--output-csv",
        default=str(DEFAULT_OUTPUT_CSV),
        help="Output machine-accepted CSV.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    ocr_csv = Path(args.ocr_csv).resolve()
    output_csv = Path(args.output_csv).resolve()

    ocr_rows = read_csv_rows(ocr_csv)

    accepted_rows = [
        build_accepted_row(row)
        for row in ocr_rows
        if row.get("status", "") in ACCEPTED_STATUSES
    ]

    write_machine_accepted(accepted_rows, output_csv)

    print(f"Read OCR CSV: {ocr_csv}")
    print(f"Wrote machine accepted CSV: {output_csv}")
    print(f"Accepted rows: {len(accepted_rows)}")

    status_counts: dict[str, int] = {}
    for row in accepted_rows:
        status = row.get("status", "")
        status_counts[status] = status_counts.get(status, 0) + 1

    print()
    print("Status counts:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())