from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from lsco_tdcj_intake.omr.checkbox import (  # noqa: E402
    CheckboxOMRConfig,
    detect_checkbox_mark,
    save_checkbox_debug_image,
)


def default_map_path(page: int) -> Path:
    """Return the locked JSON map path for the current repo layout."""
    try:
        from lsco_tdcj_intake.paths import get_page1_map_path, get_page2_map_path

        return get_page1_map_path() if page == 1 else get_page2_map_path()
    except Exception:
        form_root = REPO_ROOT / "forms" / "LSCO_TDCJ_Application_v5_green" / "maps_locked"

        if page == 1:
            return form_root / "LSCO_TDCJ_Page1_JSON_FINAL.json"

        return form_root / "LSCO_TDCJ_Page2_JSON_FINAL.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run centroid-based OMR on one locked-JSON checkbox field from a warped page PNG."
    )

    parser.add_argument("image", type=Path, help="Warped page image path.")
    parser.add_argument("--page", type=int, choices=(1, 2), required=True)
    parser.add_argument("--field", required=True)
    parser.add_argument("--map", dest="map_path", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, default=None)

    parser.add_argument(
        "--dark-threshold",
        type=int,
        default=140,
        help="Pixels <= this grayscale value count as dark.",
    )
    parser.add_argument(
        "--interior-shrink",
        type=float,
        default=0.25,
        help="Fraction trimmed from each checkbox side.",
    )
    parser.add_argument(
        "--unchecked-max",
        type=float,
        default=0.04,
        help="Max dark ratio for unchecked.",
    )
    parser.add_argument(
        "--checked-min",
        type=float,
        default=0.18,
        help="Min dark ratio for checked.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    image = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {args.image}")

    map_path = args.map_path or default_map_path(args.page)
    if not map_path.exists():
        raise FileNotFoundError(
            f"Could not find page map: {map_path}\n"
            "Pass --map explicitly if your locked JSON lives elsewhere."
        )

    with map_path.open("r", encoding="utf-8") as f:
        page_map = json.load(f)

    config = CheckboxOMRConfig(
        dark_threshold=args.dark_threshold,
        interior_shrink=args.interior_shrink,
        unchecked_max_dark_ratio=args.unchecked_max,
        checked_min_dark_ratio=args.checked_min,
    )

    result = detect_checkbox_mark(
        page_image=image,
        page_map=page_map,
        field_id=args.field,
        config=config,
    )

    save_checkbox_debug_image(args.output, image, result)

    result_dict = result.to_dict()
    print(json.dumps(result_dict, indent=2))
    print(f"\nDebug image written: {args.output}")

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(result_dict, indent=2),
            encoding="utf-8",
        )
        print(f"Result JSON written: {args.json_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())