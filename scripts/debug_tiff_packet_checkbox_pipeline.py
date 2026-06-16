from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

EXTRACT_SCRIPT = REPO_ROOT / "scripts" / "extract_tiff_frames.py"
WARP_SCRIPT = REPO_ROOT / "scripts" / "debug_warp_page.py"
PAGE_ID_SCRIPT = REPO_ROOT / "scripts" / "debug_page_identity.py"
PACKET_OMR_SCRIPT = REPO_ROOT / "scripts" / "debug_packet_checkbox_groups.py"


def run_command(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    if completed.stdout:
        print(completed.stdout)

    if completed.stderr:
        print(completed.stderr, file=sys.stderr)

    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {completed.returncode}:\n"
            + " ".join(command)
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run TIFF packet extraction, page warp, page identity guard, and checkbox OMR."
    )

    parser.add_argument("tiff_path", type=Path)
    parser.add_argument(
        "--packet-id",
        default=None,
        help="Optional packet id. Defaults to TIFF filename stem.",
    )
    parser.add_argument(
        "--working-dir",
        type=Path,
        default=Path("data/working/packet_pipeline"),
    )
    parser.add_argument("--output-json", type=Path, required=True)

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    packet_id = args.packet_id or args.tiff_path.stem
    packet_dir = args.working_dir / packet_id
    frames_dir = packet_dir / "frames"
    warped_dir = packet_dir / "warped"
    omr_working_dir = packet_dir / "checkbox_omr_work"

    packet_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)
    warped_dir.mkdir(parents=True, exist_ok=True)
    omr_working_dir.mkdir(parents=True, exist_ok=True)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)

    print(f"Packet id: {packet_id}")
    print(f"Packet dir: {packet_dir}")

    print("\nSTEP 1: Extract TIFF frames")
    run_command(
        [
            sys.executable,
            str(EXTRACT_SCRIPT),
            str(args.tiff_path),
            "--output-dir",
            str(frames_dir),
        ]
    )

    page1_frame = frames_dir / f"{args.tiff_path.stem}_frame_01.png"
    page2_frame = frames_dir / f"{args.tiff_path.stem}_frame_02.png"

    if not page1_frame.exists():
        raise FileNotFoundError(f"Expected Page 1 frame not found: {page1_frame}")

    if not page2_frame.exists():
        raise FileNotFoundError(f"Expected Page 2 frame not found: {page2_frame}")

    print("\nSTEP 2: Warp pages")
    warped_page1 = warped_dir / "warped_page_1.png"
    warped_page2 = warped_dir / "warped_page_2.png"

    run_command(
        [
            sys.executable,
            str(WARP_SCRIPT),
            str(page1_frame),
            "--output",
            str(warped_page1),
        ]
    )

    run_command(
        [
            sys.executable,
            str(WARP_SCRIPT),
            str(page2_frame),
            "--output",
            str(warped_page2),
        ]
    )

    print("\nSTEP 3: Verify page identity")
    run_command(
        [
            sys.executable,
            str(PAGE_ID_SCRIPT),
            str(warped_page1),
            "--expect-page",
            "1",
        ]
    )

    run_command(
        [
            sys.executable,
            str(PAGE_ID_SCRIPT),
            str(warped_page2),
            "--expect-page",
            "2",
        ]
    )

    print("\nSTEP 4: Run packet checkbox OMR")
    packet_omr_json = omr_working_dir / "packet_checkbox_groups.json"

    run_command(
        [
            sys.executable,
            str(PACKET_OMR_SCRIPT),
            "--page1",
            str(warped_page1),
            "--page2",
            str(warped_page2),
            "--working-dir",
            str(omr_working_dir),
            "--output-json",
            str(packet_omr_json),
        ]
    )

    with packet_omr_json.open("r", encoding="utf-8") as f:
        packet_result = json.load(f)

    pipeline_result = {
        "packet_id": packet_id,
        "source_tiff": str(args.tiff_path),
        "packet_status": packet_result.get("packet_status"),
        "review_pages": packet_result.get("review_pages", []),
        "artifacts": {
            "packet_dir": str(packet_dir),
            "frames_dir": str(frames_dir),
            "warped_page_1": str(warped_page1),
            "warped_page_2": str(warped_page2),
            "packet_checkbox_json": str(packet_omr_json),
        },
        "checkbox_omr": packet_result,
    }

    args.output_json.write_text(
        json.dumps(pipeline_result, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"Pipeline status: {pipeline_result['packet_status']}")
    print(f"Pipeline JSON written: {args.output_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())