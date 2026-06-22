from __future__ import annotations

import argparse
import csv
import json
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

DEFAULT_HUMAN_REVIEW_QUEUE_CSV = DEFAULT_REVIEW_PACKET_DIR / "human_review_queue.csv"
DEFAULT_MACHINE_ACCEPTED_CSV = DEFAULT_REVIEW_PACKET_DIR / "page1_machine_accepted.csv"
DEFAULT_CHECKBOX_SUMMARY_CSV = DEFAULT_REVIEW_PACKET_DIR / "checkbox_review_summary.csv"
DEFAULT_OUTPUT_JSON = DEFAULT_REVIEW_PACKET_DIR / "reviewed_packet.json"
DEFAULT_OUTPUT_CSV = DEFAULT_REVIEW_PACKET_DIR / "reviewed_packet_values.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Required CSV not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "packet_id",
        "field_id",
        "source",
        "final_value",
        "machine_value",
        "review_value",
        "status",
        "notes",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def clean(value: str | None) -> str:
    return str(value or "").strip()

def normalize_review_value(field_id: str, value: str) -> str:
    if not value:
        return ""

    digits = "".join(ch for ch in value if ch.isdigit())

    if field_id == "p1_date_of_birth" and len(digits) <= 8:
        return digits.zfill(8)

    if field_id == "p1_ssn" and len(digits) <= 9:
        return digits.zfill(9)

    if field_id == "p1_tdcj_number" and len(digits) <= 8:
        return digits.zfill(8)

    return value

def first_present(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = clean(row.get(name))
        if value:
            return value
    return ""


def machine_value_from_accepted(row: dict[str, str]) -> str:
    return clean(row.get("normalized_text"))


def machine_value_from_review(row: dict[str, str]) -> str:
    return clean(row.get("machine_value"))


def machine_value_from_checkbox(row: dict[str, str]) -> str:
    return first_present(
        row,
        [
            "machine_value",
            "selected",
            "selected_value",
            "suggested_selected",
            "value",
            "normalized_text",
        ],
    )


def field_id_from_checkbox(row: dict[str, str]) -> str:
    return first_present(row, ["field_id", "group_id", "id"])


def status_from_checkbox(row: dict[str, str]) -> str:
    return first_present(row, ["status", "group_status"])


def notes_from_checkbox(row: dict[str, str]) -> str:
    return first_present(
        row,
        [
            "notes",
            "reason",
            "message",
            "validation_message",
            "review_reason",
        ],
    )


def build_machine_rows(
    packet_id: str,
    machine_rows: list[dict[str, str]],
) -> dict[str, dict[str, str]]:
    values: dict[str, dict[str, str]] = {}

    for row in machine_rows:
        field_id = clean(row.get("field_id"))
        if not field_id:
            continue

        final_value = machine_value_from_accepted(row)

        values[field_id] = {
            "packet_id": packet_id,
            "field_id": field_id,
            "source": "machine_accepted",
            "final_value": final_value,
            "machine_value": final_value,
            "review_value": "",
            "status": clean(row.get("status")),
            "notes": clean(row.get("notes")),
        }

    return values


def apply_checkbox_accepted_rows(
    packet_id: str,
    values: dict[str, dict[str, str]],
    checkbox_rows: list[dict[str, str]],
) -> None:
    for row in checkbox_rows:
        status = status_from_checkbox(row)
        if status != "valid":
            continue

        field_id = field_id_from_checkbox(row)
        if not field_id:
            continue

        final_value = machine_value_from_checkbox(row)

        values[field_id] = {
            "packet_id": packet_id,
            "field_id": field_id,
            "source": "checkbox_accepted",
            "final_value": final_value,
            "machine_value": final_value,
            "review_value": "",
            "status": status,
            "notes": notes_from_checkbox(row),
        }


def apply_review_rows(
    packet_id: str,
    values: dict[str, dict[str, str]],
    review_rows: list[dict[str, str]],
) -> None:
    for row in review_rows:
        field_id = clean(row.get("field_id"))
        if not field_id:
            continue

        review_value = normalize_review_value(
            field_id,
            clean(row.get("review_value")),
        )
        machine_value = machine_value_from_review(row)

        if review_value:
            final_value = review_value
            source = "human_review"
        else:
            final_value = ""
            source = "review_pending"

        notes_parts = []

        row_notes = clean(row.get("notes"))
        if row_notes:
            notes_parts.append(row_notes)

        review_notes = clean(row.get("review_notes"))
        if review_notes:
            notes_parts.append(f"review_notes={review_notes}")

        values[field_id] = {
            "packet_id": packet_id,
            "field_id": field_id,
            "source": source,
            "final_value": final_value,
            "machine_value": machine_value,
            "review_value": review_value,
            "status": clean(row.get("status")),
            "notes": " | ".join(notes_parts),
        }


def build_payload(packet_id: str, rows: list[dict[str, str]]) -> dict:
    fields = {
        row["field_id"]: {
            "value": row["final_value"],
            "source": row["source"],
            "status": row["status"],
            "machine_value": row["machine_value"],
            "review_value": row["review_value"],
            "notes": row["notes"],
        }
        for row in rows
    }

    pending_review = [
        row["field_id"]
        for row in rows
        if row["source"] == "review_pending"
    ]

    return {
        "packet_id": packet_id,
        "status": "review_complete" if not pending_review else "review_pending",
        "field_count": len(rows),
        "pending_review_count": len(pending_review),
        "pending_review_fields": pending_review,
        "fields": fields,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build reviewed packet values from machine accepted, checkbox accepted, and human review queue CSVs."
    )

    parser.add_argument(
        "--packet-id",
        default=DEFAULT_PACKET_ID,
        help="Packet id.",
    )

    parser.add_argument(
        "--human-review-csv",
        default=str(DEFAULT_HUMAN_REVIEW_QUEUE_CSV),
        help="Input human_review_queue.csv.",
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
        "--output-json",
        default=str(DEFAULT_OUTPUT_JSON),
        help="Output reviewed_packet.json.",
    )

    parser.add_argument(
        "--output-csv",
        default=str(DEFAULT_OUTPUT_CSV),
        help="Output reviewed_packet_values.csv.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    packet_id = str(args.packet_id)
    human_review_csv = Path(args.human_review_csv).resolve()
    machine_accepted_csv = Path(args.machine_accepted_csv).resolve()
    checkbox_summary_csv = Path(args.checkbox_summary_csv).resolve()
    output_json = Path(args.output_json).resolve()
    output_csv = Path(args.output_csv).resolve()

    machine_rows = read_csv(machine_accepted_csv)
    checkbox_rows = read_csv(checkbox_summary_csv)
    review_rows = read_csv(human_review_csv)

    values = build_machine_rows(packet_id, machine_rows)
    apply_checkbox_accepted_rows(packet_id, values, checkbox_rows)
    apply_review_rows(packet_id, values, review_rows)

    final_rows = sorted(
        values.values(),
        key=lambda row: row["field_id"],
    )

    payload = build_payload(packet_id, final_rows)

    write_csv(final_rows, output_csv)
    write_json(payload, output_json)

    print(f"Packet id: {packet_id}")
    print(f"Read machine accepted CSV: {machine_accepted_csv}")
    print(f"Machine accepted rows: {len(machine_rows)}")
    print(f"Read checkbox summary CSV: {checkbox_summary_csv}")
    print(f"Checkbox source rows: {len(checkbox_rows)}")
    print(f"Read human review CSV: {human_review_csv}")
    print(f"Human review rows: {len(review_rows)}")
    print(f"Wrote reviewed values CSV: {output_csv}")
    print(f"Wrote reviewed packet JSON: {output_json}")
    print(f"Reviewed packet status: {payload['status']}")
    print(f"Pending review fields: {payload['pending_review_count']}")

    source_counts: dict[str, int] = {}
    for row in final_rows:
        source = row.get("source", "")
        source_counts[source] = source_counts.get(source, 0) + 1

    print()
    print("Source counts:")
    for source, count in sorted(source_counts.items()):
        print(f"  {source}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())