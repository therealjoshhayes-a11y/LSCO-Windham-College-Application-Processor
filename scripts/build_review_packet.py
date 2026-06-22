from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PACKET_PATH = (
    PROJECT_ROOT
    / "data"
    / "incoming"
    / "scans"
    / "image-1.tif"
)

CHECKBOX_ROOT = PROJECT_ROOT / "data" / "processed" / "checkboxes"
OCR_ROOT = PROJECT_ROOT / "data" / "working" / "ocr_debug" / "page1_ocr"
REVIEW_PACKET_ROOT = PROJECT_ROOT / "data" / "processed" / "review_packets"


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


def packet_id_from_path(packet_path: Path) -> str:
    return packet_path.stem


def copy_if_exists(source: Path, destination: Path) -> None:
    if not source.exists():
        print(f"Skipped missing artifact: {source}")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    print(f"Copied: {source} -> {destination}")


def copy_review_artifacts(packet_id: str) -> None:
    review_dir = REVIEW_PACKET_ROOT / packet_id
    review_dir.mkdir(parents=True, exist_ok=True)

    checkbox_dir = CHECKBOX_ROOT / packet_id

    artifacts = [
        (
            checkbox_dir / "packet_checkbox_groups.json",
            review_dir / "packet_checkbox_groups.json",
        ),
        (
            checkbox_dir / "review_summary.csv",
            review_dir / "checkbox_review_summary.csv",
        ),
        (
            checkbox_dir / "review_summary.json",
            review_dir / "checkbox_review_summary.json",
        ),
        (
            OCR_ROOT / "page1_ocr.csv",
            review_dir / "page1_ocr.csv",
        ),
        (
            OCR_ROOT / "page1_ocr.json",
            review_dir / "page1_ocr.json",
        ),
        (
            OCR_ROOT / "page1_review_queue.csv",
            review_dir / "page1_ocr_review_queue.csv",
        ),
        (
            OCR_ROOT / "page1_machine_accepted.csv",
            review_dir / "page1_machine_accepted.csv",
        ),
        (
            OCR_ROOT / "numeric_fullfield" / "page1_numeric_fullfield_ocr.csv",
            review_dir / "page1_numeric_fullfield_ocr.csv",
        ),
        (
            OCR_ROOT / "numeric_fullfield" / "page1_numeric_fullfield_ocr.json",
            review_dir / "page1_numeric_fullfield_ocr.json",
        ),
    ]

    print()
    print("=== Copy review artifacts ===")
    for source, destination in artifacts:
        copy_if_exists(source, destination)


def main() -> int:
    packet_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_PACKET_PATH

    if not packet_path.exists():
        print(f"Packet not found: {packet_path}", file=sys.stderr)
        return 1

    packet_id = packet_id_from_path(packet_path)
    warped_page_1 = CHECKBOX_ROOT / packet_id / "warped" / "warped_page_1.png"

    print(f"Packet path: {packet_path}")
    print(f"Packet id: {packet_id}")

    run_step(
        "Process packet checkboxes",
        [
            sys.executable,
            "scripts/process_packet_checkboxes.py",
            str(packet_path),
        ],
    )

    if not warped_page_1.exists():
        print(f"Expected warped Page 1 not found: {warped_page_1}", file=sys.stderr)
        return 1

    run_step(
        "Run Page 1 OCR",
        [
            sys.executable,
            "scripts/debug_page1_ocr.py",
            str(warped_page_1),
        ],
    )

    run_step(
        "Run numeric full-field OCR evidence",
        [
            sys.executable,
            "scripts/debug_page1_numeric_fullfield_ocr.py",
        ],
    )

    run_step(
        "Export Page 1 OCR review queue",
        [
            sys.executable,
            "scripts/export_page1_ocr_review_queue.py",
        ],
    )

    run_step(
        "Export Page 1 machine accepted values",
        [
            sys.executable,
            "scripts/export_page1_machine_accepted.py",
        ],
    )

    run_step(
        "Merge OCR and checkbox review queues",
        [
            sys.executable,
            "scripts/merge_page1_review_with_checkbox_review.py",
        ],
    )

    copy_review_artifacts(packet_id)

    final_queue = REVIEW_PACKET_ROOT / packet_id / "human_review_queue.csv"
    machine_accepted = REVIEW_PACKET_ROOT / packet_id / "page1_machine_accepted.csv"

    print()
    print("=== Review packet complete ===")
    print(f"Human review queue: {final_queue}")
    print(f"Machine accepted Page 1 values: {machine_accepted}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())