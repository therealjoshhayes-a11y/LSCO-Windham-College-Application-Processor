from __future__ import annotations

import argparse
import json
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run reusable TIFF packet checkbox OMR pipeline."
    )

    parser.add_argument("tiff_path", type=Path)
    parser.add_argument("--packet-id", default=None)
    parser.add_argument(
        "--working-dir",
        type=Path,
        default=Path("data/working/packet_pipeline"),
    )
    parser.add_argument("--output-json", type=Path, required=True)

    parser.add_argument("--dark-threshold", type=int, default=140)
    parser.add_argument("--interior-shrink", type=float, default=0.25)
    parser.add_argument("--unchecked-max", type=float, default=0.04)
    parser.add_argument("--checked-min", type=float, default=0.18)

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    config = PacketCheckboxPipelineConfig(
        dark_threshold=args.dark_threshold,
        interior_shrink=args.interior_shrink,
        unchecked_max_dark_ratio=args.unchecked_max,
        checked_min_dark_ratio=args.checked_min,
    )

    result = run_packet_checkbox_pipeline(
        tiff_path=args.tiff_path,
        packet_id=args.packet_id,
        working_dir=args.working_dir,
        output_json=args.output_json,
        config=config,
    )

    print(json.dumps(result["page_summaries"], indent=2))
    print()
    print(f"Pipeline status: {result['packet_status']}")
    print(f"Pipeline JSON written: {args.output_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())