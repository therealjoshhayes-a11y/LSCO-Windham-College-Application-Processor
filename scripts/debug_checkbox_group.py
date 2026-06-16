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
    get_checkbox_group,
    interpret_checkbox_group,
)
from lsco_tdcj_intake.packets.page_identity import require_page  # noqa: E402


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
        description="Run OMR on a named checkbox group from a warped page PNG."
    )

    parser.add_argument("image", type=Path, help="Warped page image path.")
    parser.add_argument("--page", type=int, choices=(1, 2), required=True)
    parser.add_argument("--group", required=True, help="Checkbox group id, e.g. term.")
    parser.add_argument("--map", dest="map_path", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument(
        "--debug-dir",
        type=Path,
        default=Path("data/working/checkbox_group_debug"),
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

    group = get_checkbox_group(args.page, args.group)

    config = CheckboxOMRConfig(
        dark_threshold=args.dark_threshold,
        interior_shrink=args.interior_shrink,
        unchecked_max_dark_ratio=args.unchecked_max,
        checked_min_dark_ratio=args.checked_min,
    )

    results = {}

    debug_group_dir = args.debug_dir / f"p{args.page}_{args.group}"
    debug_group_dir.mkdir(parents=True, exist_ok=True)

    for option in group.options:
        result = detect_checkbox_mark(
            page_image=image,
            page_map=page_map,
            field_id=option.field_id,
            config=config,
        )

        results[option.field_id] = result

        debug_path = debug_group_dir / f"{option.field_id}.png"
        save_checkbox_debug_image(debug_path, image, result)

        print(
            f"{option.field_id}: {result.decision} "
            f"ratio={result.dark_pixel_ratio} "
            f"confidence={result.confidence}"
        )

    interpreted = interpret_checkbox_group(group, results)
    interpreted["debug_dir"] = str(debug_group_dir)
    interpreted["config"] = {
        "dark_threshold": config.dark_threshold,
        "interior_shrink": config.interior_shrink,
        "unchecked_max_dark_ratio": config.unchecked_max_dark_ratio,
        "checked_min_dark_ratio": config.checked_min_dark_ratio,
        "min_interior_size_px": config.min_interior_size_px,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(interpreted, indent=2),
        encoding="utf-8",
    )

    print()
    print(json.dumps(interpreted, indent=2))
    print()
    print(f"Group JSON written: {args.output_json}")
    print(f"Debug crops written: {debug_group_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())