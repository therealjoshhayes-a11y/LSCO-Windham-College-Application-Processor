from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESS_SCRIPT = REPO_ROOT / "scripts" / "process_packet_checkboxes.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch process LSCO TDCJ packet TIFFs through checkbox OMR."
    )

    parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory containing packet TIFF files.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/processed/checkboxes"),
    )
    parser.add_argument(
        "--manifest-csv",
        type=Path,
        default=Path("data/processed/checkboxes/batch_manifest.csv"),
    )
    parser.add_argument(
        "--pattern",
        default="*.tif",
        help="Glob pattern for packet files. Default: *.tif",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue processing remaining packets after a failure.",
    )

    return parser.parse_args()


def run_packet(tiff_path: Path, output_root: Path) -> dict:
    command = [
        sys.executable,
        str(PROCESS_SCRIPT),
        str(tiff_path),
        "--output-root",
        str(output_root),
    ]

    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    packet_id = tiff_path.stem
    packet_root = output_root / packet_id
    packet_json = packet_root / "packet_checkbox_groups.json"
    review_json = packet_root / "review_summary.json"
    review_csv = packet_root / "review_summary.csv"
    failure_json = packet_root / "failure.json"

    status = "unknown"
    accepted_count = None
    review_count = None
    error = None

    if packet_json.exists():
        with packet_json.open("r", encoding="utf-8") as f:
            packet = json.load(f)
        status = packet.get("packet_status", "unknown")

    if review_json.exists():
        with review_json.open("r", encoding="utf-8") as f:
            review = json.load(f)
        accepted_count = review.get("accepted_count")
        review_count = review.get("review_count")

    if failure_json.exists():
        with failure_json.open("r", encoding="utf-8") as f:
            failure = json.load(f)
        status = failure.get("packet_status", "failed")
        error = failure.get("error")

    if completed.returncode not in {0, 1} and status != "needs_review":
        status = "failed"
        if not error:
            error = completed.stderr.strip() or completed.stdout.strip()

    return {
        "packet_id": packet_id,
        "source_tiff": str(tiff_path),
        "status": status,
        "return_code": completed.returncode,
        "accepted_count": accepted_count,
        "review_count": review_count,
        "packet_root": str(packet_root),
        "packet_json": str(packet_json) if packet_json.exists() else "",
        "review_json": str(review_json) if review_json.exists() else "",
        "review_csv": str(review_csv) if review_csv.exists() else "",
        "failure_json": str(failure_json) if failure_json.exists() else "",
        "error": error or "",
    }


def write_manifest(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "packet_id",
        "source_tiff",
        "status",
        "return_code",
        "accepted_count",
        "review_count",
        "packet_root",
        "packet_json",
        "review_json",
        "review_csv",
        "failure_json",
        "error",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()

    if not args.input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {args.input_dir}")

    tiff_paths = sorted(args.input_dir.glob(args.pattern))

    if not tiff_paths:
        print(f"No files found in {args.input_dir} matching {args.pattern}")
        return 1

    rows: list[dict] = []

    for index, tiff_path in enumerate(tiff_paths, start=1):
        print(f"[{index}/{len(tiff_paths)}] Processing {tiff_path}")

        row = run_packet(tiff_path, args.output_root)
        rows.append(row)

        print(
            f"  status={row['status']} "
            f"accepted={row['accepted_count']} "
            f"review={row['review_count']}"
        )

        if row["status"] == "failed" and not args.continue_on_error:
            write_manifest(args.manifest_csv, rows)
            print(f"Batch manifest written: {args.manifest_csv}")
            return 2

    write_manifest(args.manifest_csv, rows)

    failed_count = sum(1 for row in rows if row["status"] == "failed")
    review_count = sum(1 for row in rows if row["status"] == "needs_review")
    valid_count = sum(1 for row in rows if row["status"] == "valid")

    print()
    print(f"Packets processed: {len(rows)}")
    print(f"Valid: {valid_count}")
    print(f"Needs review: {review_count}")
    print(f"Failed: {failed_count}")
    print(f"Batch manifest written: {args.manifest_csv}")

    return 2 if failed_count else 0


if __name__ == "__main__":
    raise SystemExit(main())