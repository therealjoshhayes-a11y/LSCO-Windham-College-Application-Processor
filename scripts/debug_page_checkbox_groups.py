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
from lsco_tdcj_intake.omr.checkbox_groups import (  # noqa: E402
    CHECKBOX_GROUPS,
    interpret_checkbox_group,
)
from lsco_tdcj_intake.packets.page_identity import require_page  # noqa: E402


def default_map_path(page: int) -> Path:
    try:
        from lsco_tdcj_intake.paths import get_page1_map_path, get_page2_map_path

        return get_page1_map_path() if page == 1 else get_page2_map_path()
    except Exception:
        form_root = REPO_ROOT / "forms" / "LSCO_TDCJ_Application_v5_green" / "maps_locked"
        if page == 1:
            return form_root / "LSCO_TDCJ_Page1_JSON_FINAL.json"
        return form_root / "LSCO_TDCJ_Page2_JSON_FINAL.json"


def page_groups(page: int):
    return [
        group
        for (group_page, _group_id), group in sorted(CHECKBOX_GROUPS.items())
        if group_page == page
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run all known checkbox groups for one warped page image."
    )

    parser.add_argument("image", type=Path, help="Warped page image path.")
    parser.add_argument("--page", type=int, choices=(1, 2), required=True)
    parser.add_argument("--map", dest="map_path", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument(
        "--debug-dir",
        type=Path,
        default=Path("data/working/page_checkbox_debug"),
    )

    parser.add_argument("--dark-threshold", type=int, default=140)
    parser.add_argument("--interior-shrink", type=float, default=0.25)
    parser.add_argument("--unchecked-max", type=float, default=0.04)
    parser.add_argument("--checked-min", type=float, default=0.18)

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    image = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {args.image}")

    identity = require_page(args.image, args.page)
    print(
        f"Page identity OK: expected={args.page} "
        f"predicted={identity.predicted_page} "
        f"confidence={identity.confidence}"
    )

    map_path = args.map_path or default_map_path(args.page)
    if not map_path.exists():
        raise FileNotFoundError(f"Could not find page map: {map_path}")

    with map_path.open("r", encoding="utf-8") as f:
        page_map = json.load(f)

    groups = page_groups(args.page)
    if not groups:
        raise KeyError(f"No checkbox groups defined for page {args.page}")

    config = CheckboxOMRConfig(
        dark_threshold=args.dark_threshold,
        interior_shrink=args.interior_shrink,
        unchecked_max_dark_ratio=args.unchecked_max,
        checked_min_dark_ratio=args.checked_min,
    )

    page_debug_dir = args.debug_dir / f"p{args.page}"
    page_debug_dir.mkdir(parents=True, exist_ok=True)

    interpreted_groups = {}

    for group in groups:
        print()
        print(f"Group: {group.group_id}")

        group_results = {}
        group_debug_dir = page_debug_dir / group.group_id
        group_debug_dir.mkdir(parents=True, exist_ok=True)

        for option in group.options:
            result = detect_checkbox_mark(
                page_image=image,
                page_map=page_map,
                field_id=option.field_id,
                config=config,
            )

            group_results[option.field_id] = result

            debug_path = group_debug_dir / f"{option.field_id}.png"
            save_checkbox_debug_image(debug_path, image, result)

            print(
                f"  {option.field_id}: {result.decision} "
                f"ratio={result.dark_pixel_ratio} "
                f"confidence={result.confidence}"
            )

        interpreted = interpret_checkbox_group(group, group_results)
        interpreted["debug_dir"] = str(group_debug_dir)
        interpreted_groups[group.group_id] = interpreted

    invalid_groups = [
        group_id
        for group_id, group_result in interpreted_groups.items()
        if group_result["status"] != "valid"
    ]

    overall_status = "valid" if not invalid_groups else "needs_review"

    page_result = {
        "page_number": args.page,
        "image_path": str(args.image),
        "page_identity": {
            "decision": identity.decision,
            "predicted_page": identity.predicted_page,
            "confidence": identity.confidence,
            "page1_score": identity.page1_score,
            "page2_score": identity.page2_score,
        },
        "overall_status": overall_status,
        "invalid_or_review_groups": invalid_groups,
        "groups": interpreted_groups,
        "debug_dir": str(page_debug_dir),
        "config": {
            "dark_threshold": config.dark_threshold,
            "interior_shrink": config.interior_shrink,
            "unchecked_max_dark_ratio": config.unchecked_max_dark_ratio,
            "checked_min_dark_ratio": config.checked_min_dark_ratio,
            "min_interior_size_px": config.min_interior_size_px,
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(page_result, indent=2),
        encoding="utf-8",
    )

    print()
    print(json.dumps(page_result, indent=2))
    print()
    print(f"Page checkbox JSON written: {args.output_json}")
    print(f"Debug crops written: {page_debug_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())