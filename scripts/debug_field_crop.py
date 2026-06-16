from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from lsco_tdcj_intake.form_maps.loader import load_form_map  # noqa: E402
from lsco_tdcj_intake.imaging.field_cropper import (  # noqa: E402
    CropPadding,
    crop_field_from_file,
    save_crop_result,
)
from lsco_tdcj_intake.packets.page_identity import require_page  # noqa: E402
from lsco_tdcj_intake.paths import get_page1_map_path, get_page2_map_path  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crop one mapped field from a warped LSCO TDCJ page image."
    )

    parser.add_argument("warped_image", type=Path)
    parser.add_argument("--page", type=int, required=True, choices=[1, 2])
    parser.add_argument("--field-id", required=True)
    parser.add_argument("--output-image", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--dpi", type=int, default=300)

    parser.add_argument("--pad-left", type=int, default=None)
    parser.add_argument("--pad-top", type=int, default=None)
    parser.add_argument("--pad-right", type=int, default=None)
    parser.add_argument("--pad-bottom", type=int, default=None)

    return parser.parse_args()


def optional_padding(args: argparse.Namespace) -> CropPadding | None:
    values = [args.pad_left, args.pad_top, args.pad_right, args.pad_bottom]

    if all(value is None for value in values):
        return None

    return CropPadding(
        left=args.pad_left or 0,
        top=args.pad_top or 0,
        right=args.pad_right or 0,
        bottom=args.pad_bottom or 0,
    )


def main() -> int:
    args = parse_args()

    identity = require_page(args.warped_image, args.page)
    map_path = get_page1_map_path() if args.page == 1 else get_page2_map_path()
    form_map = load_form_map(map_path)

    crop = crop_field_from_file(
        warped_image_path=args.warped_image,
        form_map=form_map,
        field_id=args.field_id,
        dpi=args.dpi,
        padding=optional_padding(args),
    )

    save_crop_result(crop, args.output_image)

    metadata = {
        "warped_image": str(args.warped_image),
        "page_identity": asdict(identity),
        "page_number": crop.page_number,
        "field_id": crop.field_id,
        "base_box": crop.base_box,
        "final_box": crop.final_box,
        "padding": asdict(crop.padding),
        "output_image": str(args.output_image),
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print(f"Page identity OK: expected={args.page} predicted={identity.predicted_page}")
    print(f"Field crop written: {args.output_image}")
    print(f"Crop metadata written: {args.output_json}")
    print(f"Base box: {crop.base_box}")
    print(f"Final box: {crop.final_box}")
    print(f"Padding: {asdict(crop.padding)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())