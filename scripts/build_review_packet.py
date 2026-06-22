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
SHARED_OCR_ROOT = PROJECT_ROOT / "data" / "working" / "ocr_debug" / "page1_ocr"
PACKET_OCR_PARENT = PROJECT_ROOT / "data" / "working" / "ocr_debug"
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


def packet_ocr_root(packet_id: str) -> Path:
    return PACKET_OCR_PARENT / packet_id / "page1_ocr"


def copy_review_artifacts(packet_id: str) -> None:
    review_dir = REVIEW_PACKET_ROOT / packet_id
    review_dir.mkdir(parents=True, exist_ok=True)

    checkbox_dir = CHECKBOX_ROOT / packet_id
    ocr_dir = packet_ocr_root(packet_id)

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
            SHARED_OCR_ROOT / "page1_ocr.csv",
            review_dir / "page1_ocr.csv",
        ),
        (
            SHARED_OCR_ROOT / "page1_ocr.json",
            review_dir / "page1_ocr.json",
        ),
        (
            ocr_dir / "page1_review_queue.csv",
            review_dir / "page1_ocr_review_queue.csv",
        ),
        (
            ocr_dir / "page1_machine_accepted.csv",
            review_dir / "page1_machine_accepted.csv",
        ),
        (
            ocr_dir / "numeric_fullfield" / "page1_numeric_fullfield_ocr.csv",
            review_dir / "page1_numeric_fullfield_ocr.csv",
        ),
        (
            ocr_dir / "numeric_fullfield" / "page1_numeric_fullfield_ocr.json",
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

    checkbox_dir = CHECKBOX_ROOT / packet_id
    checkbox_review_csv = checkbox_dir / "review_summary.csv"
    warped_page_1 = checkbox_dir / "warped" / "warped_page_1.png"

    ocr_dir = packet_ocr_root(packet_id)
    numeric_dir = ocr_dir / "numeric_fullfield"
    page1_review_queue_csv = ocr_dir / "page1_review_queue.csv"
    page1_machine_accepted_csv = ocr_dir / "page1_machine_accepted.csv"

    review_dir = REVIEW_PACKET_ROOT / packet_id
    human_review_queue_csv = review_dir / "human_review_queue.csv"

    print(f"Packet path: {packet_path}")
    print(f"Packet id: {packet_id}")
    print(f"Packet OCR dir: {ocr_dir}")
    print(f"Review packet dir: {review_dir}")

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
            "--crops-dir",
            str(SHARED_OCR_ROOT / "crops"),
            "--output-dir",
            str(numeric_dir),
        ],
    )

    run_step(
        "Export Page 1 OCR review queue",
        [
            sys.executable,
            "scripts/export_page1_ocr_review_queue.py",
            "--ocr-csv",
            str(SHARED_OCR_ROOT / "page1_ocr.csv"),
            "--numeric-fullfield-csv",
            str(numeric_dir / "page1_numeric_fullfield_ocr.csv"),
            "--output-csv",
            str(page1_review_queue_csv),
        ],
    )

    run_step(
        "Export Page 1 machine accepted values",
        [
            sys.executable,
            "scripts/export_page1_machine_accepted.py",
            "--ocr-csv",
            str(SHARED_OCR_ROOT / "page1_ocr.csv"),
            "--output-csv",
            str(page1_machine_accepted_csv),
        ],
    )

    run_step(
        "Merge OCR and checkbox review queues",
        [
            sys.executable,
            "scripts/merge_page1_review_with_checkbox_review.py",
            "--packet-id",
            packet_id,
            "--checkbox-review-csv",
            str(checkbox_review_csv),
            "--ocr-review-csv",
            str(page1_review_queue_csv),
            "--output-csv",
            str(human_review_queue_csv),
        ],
    )

    copy_review_artifacts(packet_id)

    print()
    print("=== Review packet complete ===")
    print(f"Human review queue: {human_review_queue_csv}")
    print(f"Machine accepted Page 1 values: {page1_machine_accepted_csv}")
    print(f"Packet OCR artifacts: {ocr_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())