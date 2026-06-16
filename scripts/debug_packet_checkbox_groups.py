from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PAGE_RUNNER = REPO_ROOT / "scripts" / "debug_page_checkbox_groups.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run checkbox OMR groups for both pages of one packet."
    )

    parser.add_argument("--page1", type=Path, required=True, help="Warped Page 1 image.")
    parser.add_argument("--page2", type=Path, required=True, help="Warped Page 2 image.")
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument(
        "--working-dir",
        type=Path,
        default=Path("data/working/packet_checkbox_debug"),
    )

    return parser.parse_args()


def run_page_runner(
    image_path: Path,
    page_number: int,
    output_json: Path,
) -> dict:
    command = [
        sys.executable,
        str(PAGE_RUNNER),
        str(image_path),
        "--page",
        str(page_number),
        "--output-json",
        str(output_json),
    ]

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
            f"Page {page_number} checkbox runner failed with exit code "
            f"{completed.returncode}"
        )

    with output_json.open("r", encoding="utf-8") as f:
        return json.load(f)


def summarize_page(page_result: dict) -> dict:
    groups = page_result.get("groups", {})

    accepted: dict[str, list[str]] = {}
    suggested: dict[str, list[str]] = {}
    invalid_or_review: list[str] = []

    for group_id, group_result in groups.items():
        selected = group_result.get("selected", [])
        suggested_selected = group_result.get("suggested_selected", [])
        status = group_result.get("status")

        if selected:
            accepted[group_id] = selected

        if suggested_selected:
            suggested[group_id] = suggested_selected

        if status != "valid":
            invalid_or_review.append(group_id)

    return {
        "page_number": page_result.get("page_number"),
        "overall_status": page_result.get("overall_status"),
        "accepted": accepted,
        "suggested": suggested,
        "invalid_or_review_groups": invalid_or_review,
    }


def main() -> int:
    args = parse_args()

    args.working_dir.mkdir(parents=True, exist_ok=True)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)

    page1_json = args.working_dir / "page_1_checkbox_groups.json"
    page2_json = args.working_dir / "page_2_checkbox_groups.json"

    page1_result = run_page_runner(args.page1, 1, page1_json)
    page2_result = run_page_runner(args.page2, 2, page2_json)

    page_summaries = {
        "page_1": summarize_page(page1_result),
        "page_2": summarize_page(page2_result),
    }

    review_pages = [
        page_key
        for page_key, summary in page_summaries.items()
        if summary["overall_status"] != "valid"
    ]

    packet_status = "valid" if not review_pages else "needs_review"

    packet_result = {
        "packet_status": packet_status,
        "review_pages": review_pages,
        "page_summaries": page_summaries,
        "pages": {
            "page_1": page1_result,
            "page_2": page2_result,
        },
        "artifacts": {
            "page_1_json": str(page1_json),
            "page_2_json": str(page2_json),
        },
    }

    args.output_json.write_text(
        json.dumps(packet_result, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(packet_result["page_summaries"], indent=2))
    print()
    print(f"Packet status: {packet_status}")
    print(f"Packet checkbox JSON written: {args.output_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())