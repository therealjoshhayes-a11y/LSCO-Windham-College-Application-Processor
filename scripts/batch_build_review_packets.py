from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "incoming" / "scans"
DEFAULT_OUTPUT_MANIFEST = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "review_packets"
    / "batch_review_manifest.csv"
)

REVIEW_PACKET_ROOT = PROJECT_ROOT / "data" / "processed" / "review_packets"


@dataclass
class BatchReviewManifestRow:
    packet_id: str
    source_path: str
    status: str
    review_packet_dir: str
    human_review_queue_path: str
    machine_accepted_path: str
    error: str


def packet_id_from_path(packet_path: Path) -> str:
    return packet_path.stem


def find_packet_files(input_dir: Path) -> list[Path]:
    packet_files: list[Path] = []

    for pattern in ("*.tif", "*.tiff", "*.TIF", "*.TIFF"):
        packet_files.extend(input_dir.glob(pattern))

    return sorted(set(packet_files))


def build_one_packet(packet_path: Path) -> BatchReviewManifestRow:
    packet_id = packet_id_from_path(packet_path)
    review_packet_dir = REVIEW_PACKET_ROOT / packet_id
    human_review_queue_path = review_packet_dir / "human_review_queue.csv"
    machine_accepted_path = review_packet_dir / "page1_machine_accepted.csv"

    command = [
        sys.executable,
        "scripts/build_review_packet.py",
        str(packet_path),
    ]

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        error_text = "\n".join(
            part
            for part in [
                result.stdout.strip(),
                result.stderr.strip(),
            ]
            if part
        )

        return BatchReviewManifestRow(
            packet_id=packet_id,
            source_path=str(packet_path),
            status="failed",
            review_packet_dir=str(review_packet_dir),
            human_review_queue_path=str(human_review_queue_path),
            machine_accepted_path=str(machine_accepted_path),
            error=error_text,
        )

    missing_outputs = []

    if not human_review_queue_path.exists():
        missing_outputs.append(str(human_review_queue_path))

    if not machine_accepted_path.exists():
        missing_outputs.append(str(machine_accepted_path))

    if missing_outputs:
        return BatchReviewManifestRow(
            packet_id=packet_id,
            source_path=str(packet_path),
            status="failed_missing_outputs",
            review_packet_dir=str(review_packet_dir),
            human_review_queue_path=str(human_review_queue_path),
            machine_accepted_path=str(machine_accepted_path),
            error="Missing expected output(s): " + "; ".join(missing_outputs),
        )

    return BatchReviewManifestRow(
        packet_id=packet_id,
        source_path=str(packet_path),
        status="completed",
        review_packet_dir=str(review_packet_dir),
        human_review_queue_path=str(human_review_queue_path),
        machine_accepted_path=str(machine_accepted_path),
        error="",
    )


def write_manifest(rows: list[BatchReviewManifestRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "packet_id",
        "source_path",
        "status",
        "review_packet_dir",
        "human_review_queue_path",
        "machine_accepted_path",
        "error",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build review packets for all TIFF scans in a folder."
    )

    parser.add_argument(
        "input_dir",
        nargs="?",
        default=str(DEFAULT_INPUT_DIR),
        help="Folder containing .tif/.tiff packet scans.",
    )

    parser.add_argument(
        "--manifest-csv",
        default=str(DEFAULT_OUTPUT_MANIFEST),
        help="Output CSV manifest path.",
    )

    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop the batch on the first failed packet.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_dir = Path(args.input_dir).resolve()
    manifest_path = Path(args.manifest_csv).resolve()

    if not input_dir.exists():
        print(f"Input folder not found: {input_dir}", file=sys.stderr)
        return 1

    packet_files = find_packet_files(input_dir)

    if not packet_files:
        print(f"No TIFF packet files found in: {input_dir}", file=sys.stderr)
        return 1

    rows: list[BatchReviewManifestRow] = []

    print(f"Input folder: {input_dir}")
    print(f"Packets found: {len(packet_files)}")
    print()

    for index, packet_path in enumerate(packet_files, start=1):
        packet_id = packet_id_from_path(packet_path)

        print(f"[{index}/{len(packet_files)}] Building review packet: {packet_id}")

        try:
            row = build_one_packet(packet_path)
        except Exception as exc:
            row = BatchReviewManifestRow(
                packet_id=packet_id,
                source_path=str(packet_path),
                status="failed_exception",
                review_packet_dir=str(REVIEW_PACKET_ROOT / packet_id),
                human_review_queue_path=str(
                    REVIEW_PACKET_ROOT / packet_id / "human_review_queue.csv"
                ),
                machine_accepted_path=str(
                    REVIEW_PACKET_ROOT / packet_id / "page1_machine_accepted.csv"
                ),
                error=f"{exc}\n{traceback.format_exc()}",
            )

        rows.append(row)

        if row.status == "completed":
            print(f"  completed: {row.review_packet_dir}")
        else:
            print(f"  {row.status}: {row.error}")

            if args.stop_on_error:
                break

    write_manifest(rows, manifest_path)

    completed_count = sum(1 for row in rows if row.status == "completed")
    failed_count = len(rows) - completed_count

    print()
    print(f"Manifest written: {manifest_path}")
    print(f"Packets attempted: {len(rows)}")
    print(f"Completed: {completed_count}")
    print(f"Failed: {failed_count}")

    return 0 if failed_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())