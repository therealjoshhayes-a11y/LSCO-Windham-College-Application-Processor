from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create compact reviewer summary from packet checkbox OMR JSON."
    )

    parser.add_argument("packet_json", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, default=None)

    return parser.parse_args()


def summarize_group(page_key: str, group_id: str, group: dict) -> dict:
    rows = []

    selected = set(group.get("selected", []))
    suggested = set(group.get("suggested_selected", []))
    uncertain = set(group.get("uncertain", []))

    for field_id, field in group.get("fields", {}).items():
        value = field.get("value")

        if value in selected:
            review_state = "accepted"
        elif value in suggested:
            review_state = "suggested_review"
        elif value in uncertain:
            review_state = "uncertain_review"
        else:
            review_state = "not_selected"

        rows.append(
            {
                "page": page_key,
                "group_id": group_id,
                "group_label": group.get("label"),
                "group_status": group.get("status"),
                "field_id": field_id,
                "value": value,
                "label": field.get("label"),
                "review_state": review_state,
                "decision": field.get("decision"),
                "checked": field.get("checked"),
                "confidence": field.get("confidence"),
                "dark_pixel_ratio": field.get("dark_pixel_ratio"),
                "debug_dir": group.get("debug_dir"),
            }
        )

    return {
        "group_id": group_id,
        "label": group.get("label"),
        "status": group.get("status"),
        "message": group.get("message"),
        "selected": group.get("selected", []),
        "suggested_selected": group.get("suggested_selected", []),
        "uncertain": group.get("uncertain", []),
        "debug_dir": group.get("debug_dir"),
        "rows": rows,
    }


def build_review_summary(packet: dict) -> dict:
    pages = packet.get("pages", {})

    page_summaries = {}
    review_rows = []
    accepted_rows = []

    for page_key, page in pages.items():
        groups = page.get("groups", {})
        summarized_groups = {}

        for group_id, group in groups.items():
            summarized = summarize_group(page_key, group_id, group)
            summarized_groups[group_id] = {
                key: value
                for key, value in summarized.items()
                if key != "rows"
            }

            for row in summarized["rows"]:
                if row["review_state"] in {"suggested_review", "uncertain_review"}:
                    review_rows.append(row)
                elif row["review_state"] == "accepted":
                    accepted_rows.append(row)

        page_summaries[page_key] = {
            "page_number": page.get("page_number"),
            "overall_status": page.get("overall_status"),
            "invalid_or_review_groups": page.get("invalid_or_review_groups", []),
            "groups": summarized_groups,
        }

    return {
        "packet_id": packet.get("packet_id"),
        "source_tiff": packet.get("source_tiff"),
        "packet_status": packet.get("packet_status"),
        "review_pages": packet.get("review_pages", []),
        "accepted_count": len(accepted_rows),
        "review_count": len(review_rows),
        "accepted": accepted_rows,
        "needs_review": review_rows,
        "page_summaries": page_summaries,
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "page",
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
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()

    with args.packet_json.open("r", encoding="utf-8") as f:
        packet = json.load(f)

    summary = build_review_summary(packet)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    if args.output_csv:
        combined_rows = summary["needs_review"] + summary["accepted"]
        write_csv(args.output_csv, combined_rows)

    print(f"Packet status: {summary['packet_status']}")
    print(f"Accepted fields: {summary['accepted_count']}")
    print(f"Review fields: {summary['review_count']}")
    print(f"Review JSON written: {args.output_json}")

    if args.output_csv:
        print(f"Review CSV written: {args.output_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())