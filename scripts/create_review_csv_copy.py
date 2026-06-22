from __future__ import annotations

import argparse
import csv
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

DEFAULT_INPUT_CSV = DEFAULT_REVIEW_PACKET_DIR / "human_review_queue.csv"
DEFAULT_OUTPUT_CSV = DEFAULT_REVIEW_PACKET_DIR / "human_review_queue_FOR_REVIEW.csv"


REVIEW_COLUMNS = [
    "packet_id",
    "review_source",
    "field_id",
    "label",
    "machine_value",
    "numeric_fullfield_digits",
    "numeric_shape_valid",
    "review_value",
    "review_notes",
    "status",
    "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Input review queue not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def clean(value: str | None) -> str:
    return str(value or "").strip()


def first_present(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = clean(row.get(name))
        if value:
            return value
    return ""


def reviewer_label(row: dict[str, str]) -> str:
    return first_present(
        row,
        [
            "label",
            "field_label",
            "group_label",
            "field_id",
        ],
    )


def reviewer_machine_value(row: dict[str, str]) -> str:
    return first_present(
        row,
        [
            "machine_value",
            "normalized_text",
            "selected",
            "selected_value",
            "suggested_selected",
            "numeric_fullfield_candidate",
        ],
    )


def numeric_shape_valid(row: dict[str, str]) -> str:
    notes = clean(row.get("notes"))

    if "numeric_shape_valid=True" in notes:
        return "True"

    if "numeric_shape_valid=False" in notes:
        return "False"

    return ""


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "packet_id": clean(row.get("packet_id")),
        "review_source": clean(row.get("review_source")),
        "field_id": clean(row.get("field_id")),
        "label": reviewer_label(row),
        "machine_value": reviewer_machine_value(row),
        "numeric_fullfield_digits": clean(row.get("numeric_fullfield_candidate")),
        "numeric_shape_valid": numeric_shape_valid(row),
        "review_value": clean(row.get("review_value")),
        "review_notes": clean(row.get("review_notes")),
        "status": clean(row.get("status")),
        "notes": clean(row.get("notes")),
    }


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a reviewer-facing CSV copy from human_review_queue.csv."
    )

    parser.add_argument(
        "--input-csv",
        default=str(DEFAULT_INPUT_CSV),
        help="Input human_review_queue.csv.",
    )

    parser.add_argument(
        "--output-csv",
        default=str(DEFAULT_OUTPUT_CSV),
        help="Output reviewer-facing CSV copy.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_csv = Path(args.input_csv).resolve()
    output_csv = Path(args.output_csv).resolve()

    rows = read_csv(input_csv)
    reviewer_rows = [normalize_row(row) for row in rows]

    write_csv(reviewer_rows, output_csv)

    print(f"Read human review queue: {input_csv}")
    print(f"Rows read: {len(rows)}")
    print(f"Wrote reviewer CSV copy: {output_csv}")
    print(f"Rows written: {len(reviewer_rows)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())