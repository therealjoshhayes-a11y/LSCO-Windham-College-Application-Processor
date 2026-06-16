from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build merged checkbox review queue from processed packet folders."
    )

    parser.add_argument(
        "processed_root",
        type=Path,
        help="Root folder containing processed packet checkbox outputs.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--include-accepted",
        action="store_true",
        help="Include accepted rows as well as review rows.",
    )

    return parser.parse_args()


def load_packet_review_summary(packet_dir: Path) -> dict | None:
    review_json = packet_dir / "review_summary.json"

    if not review_json.exists():
        return None

    with review_json.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_row(packet_dir: Path, row: dict) -> dict:
    return {
        "packet_id": row.get("packet_id"),
        "packet_status": row.get("packet_status"),
        "page": row.get("page"),
        "page_number": row.get("page_number"),
        "group_id": row.get("group_id"),
        "group_label": row.get("group_label"),
        "group_status": row.get("group_status"),
        "field_id": row.get("field_id"),
        "value": row.get("value"),
        "label": row.get("label"),
        "review_state": row.get("review_state"),
        "decision": row.get("decision"),
        "checked": row.get("checked"),
        "confidence": row.get("confidence"),
        "dark_pixel_ratio": row.get("dark_pixel_ratio"),
        "debug_dir": row.get("debug_dir"),
        "packet_dir": str(packet_dir),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "packet_id",
        "packet_status",
        "page",
        "page_number",
        "group_id",
        "group_label",
        "group_status",
        "field_id",
        "value",
        "label",
        "review_state",
        "decision",
        "checked",
        "confidence",
        "dark_pixel_ratio",
        "debug_dir",
        "packet_dir",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()

    if not args.processed_root.exists():
        raise FileNotFoundError(f"Processed root does not exist: {args.processed_root}")

    packet_dirs = sorted(
        path
        for path in args.processed_root.iterdir()
        if path.is_dir()
    )

    rows: list[dict] = []
    packet_summaries: list[dict] = []

    for packet_dir in packet_dirs:
        summary = load_packet_review_summary(packet_dir)

        if summary is None:
            continue

        needs_review = [
            normalize_row(packet_dir, row)
            for row in summary.get("needs_review", [])
        ]

        accepted = [
            normalize_row(packet_dir, row)
            for row in summary.get("accepted", [])
        ]

        packet_rows = needs_review + accepted if args.include_accepted else needs_review
        rows.extend(packet_rows)

        packet_summaries.append(
            {
                "packet_id": summary.get("packet_id"),
                "packet_status": summary.get("packet_status"),
                "accepted_count": summary.get("accepted_count"),
                "review_count": summary.get("review_count"),
                "packet_dir": str(packet_dir),
            }
        )

    queue = {
        "processed_root": str(args.processed_root),
        "packet_count": len(packet_summaries),
        "row_count": len(rows),
        "include_accepted": args.include_accepted,
        "packets": packet_summaries,
        "rows": rows,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(queue, indent=2),
        encoding="utf-8",
    )

    write_csv(args.output_csv, rows)

    print(f"Packets included: {queue['packet_count']}")
    print(f"Queue rows: {queue['row_count']}")
    print(f"Review queue JSON: {args.output_json}")
    print(f"Review queue CSV: {args.output_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())