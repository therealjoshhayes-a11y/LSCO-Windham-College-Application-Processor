from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from lsco_tdcj_intake.packets.checkbox_pipeline import (  # noqa: E402
    PacketCheckboxPipelineConfig,
    run_packet_checkbox_pipeline,
)


STATUS_VALID = "valid"
STATUS_NEEDS_REVIEW = "needs_review"
STATUS_FAILED = "failed"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process one LSCO TDCJ packet TIFF through checkbox OMR."
    )

    parser.add_argument("tiff_path", type=Path)
    parser.add_argument(
        "--packet-id",
        default=None,
        help="Optional packet id. Defaults to TIFF filename stem.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/processed/checkboxes"),
        help="Root output directory for packet checkbox results.",
    )

    parser.add_argument("--dark-threshold", type=int, default=140)
    parser.add_argument("--interior-shrink", type=float, default=0.25)
    parser.add_argument("--unchecked-max", type=float, default=0.04)
    parser.add_argument("--checked-min", type=float, default=0.18)

    return parser.parse_args()


def review_rows_from_packet(packet: dict) -> list[dict]:
    rows: list[dict] = []

    for page_key, page in packet.get("pages", {}).items():
        for group_id, group in page.get("groups", {}).items():
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

                if review_state == "not_selected":
                    continue

                rows.append(
                    {
                        "packet_id": packet.get("packet_id"),
                        "packet_status": packet.get("packet_status"),
                        "page": page_key,
                        "page_number": page.get("page_number"),
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

    return rows


def build_review_summary(packet: dict) -> dict:
    rows = review_rows_from_packet(packet)

    accepted = [row for row in rows if row["review_state"] == "accepted"]
    needs_review = [
        row
        for row in rows
        if row["review_state"] in {"suggested_review", "uncertain_review"}
    ]

    return {
        "packet_id": packet.get("packet_id"),
        "source_tiff": packet.get("source_tiff"),
        "packet_status": packet.get("packet_status"),
        "review_pages": packet.get("review_pages", []),
        "accepted_count": len(accepted),
        "review_count": len(needs_review),
        "accepted": accepted,
        "needs_review": needs_review,
        "page_summaries": packet.get("page_summaries", {}),
        "artifacts": packet.get("artifacts", {}),
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


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
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()

    packet_id = args.packet_id or args.tiff_path.stem
    packet_root = args.output_root / packet_id
    packet_json = packet_root / "packet_checkbox_groups.json"
    review_json = packet_root / "review_summary.json"
    review_csv = packet_root / "review_summary.csv"
    source_copy = packet_root / "source" / args.tiff_path.name

    packet_root.mkdir(parents=True, exist_ok=True)
    source_copy.parent.mkdir(parents=True, exist_ok=True)

    config = PacketCheckboxPipelineConfig(
        dark_threshold=args.dark_threshold,
        interior_shrink=args.interior_shrink,
        unchecked_max_dark_ratio=args.unchecked_max,
        checked_min_dark_ratio=args.checked_min,
    )

    try:
        shutil.copy2(args.tiff_path, source_copy)

        packet = run_packet_checkbox_pipeline(
            tiff_path=args.tiff_path,
            packet_id=packet_id,
            working_dir=args.output_root,
            output_json=packet_json,
            config=config,
        )

        summary = build_review_summary(packet)
        write_json(review_json, summary)
        write_csv(review_csv, summary["needs_review"] + summary["accepted"])

        status = packet.get("packet_status", STATUS_FAILED)

        print(f"Packet id: {packet_id}")
        print(f"Packet status: {status}")
        print(f"Accepted fields: {summary['accepted_count']}")
        print(f"Review fields: {summary['review_count']}")
        print(f"Packet root: {packet_root}")
        print(f"Packet JSON: {packet_json}")
        print(f"Review JSON: {review_json}")
        print(f"Review CSV: {review_csv}")

        return 0 if status in {STATUS_VALID, STATUS_NEEDS_REVIEW} else 2

    except Exception as exc:
        failure = {
            "packet_id": packet_id,
            "source_tiff": str(args.tiff_path),
            "packet_status": STATUS_FAILED,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "packet_root": str(packet_root),
        }

        failure_json = packet_root / "failure.json"
        write_json(failure_json, failure)

        print(f"Packet id: {packet_id}")
        print(f"Packet status: {STATUS_FAILED}")
        print(f"Failure JSON: {failure_json}")
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)

        return 2


if __name__ == "__main__":
    raise SystemExit(main())