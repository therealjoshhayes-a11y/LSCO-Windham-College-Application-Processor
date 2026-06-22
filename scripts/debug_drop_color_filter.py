from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from lsco_tdcj_intake.imaging.drop_color import build_drop_color_mask_bgr, remove_drop_color_bgr


DEFAULT_INPUT_ROOT = Path("data/working/ocr_debug/page1_ocr/crops")
DEFAULT_OUTPUT_ROOT = Path("data/working/ocr_debug/drop_color_filter")

DEFAULT_FIELDS = [
    "p1_last_name",
    "p1_first_name",
    "p1_tdcj_number",
    "p1_hs_state",
    "p1_prev_college_row2_name",
]


def debug_one_crop(input_path: Path, output_root: Path) -> None:
    image = cv2.imread(str(input_path), cv2.IMREAD_COLOR)

    if image is None:
        raise FileNotFoundError(f"Could not read crop: {input_path}")

    mask = build_drop_color_mask_bgr(image)
    cleaned = remove_drop_color_bgr(image)

    output_root.mkdir(parents=True, exist_ok=True)

    stem = input_path.stem

    cv2.imwrite(str(output_root / f"{stem}_original.png"), image)
    cv2.imwrite(str(output_root / f"{stem}_drop_mask.png"), mask)
    cv2.imwrite(str(output_root / f"{stem}_cleaned.png"), cleaned)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write original/mask/cleaned crop images for LSCO green drop-color debugging."
    )
    parser.add_argument(
        "--input-root",
        type=Path,
        default=DEFAULT_INPUT_ROOT,
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
    )
    parser.add_argument(
        "--fields",
        nargs="*",
        default=DEFAULT_FIELDS,
    )

    args = parser.parse_args()

    for field_id in args.fields:
        input_path = args.input_root / f"{field_id}.png"
        debug_one_crop(input_path, args.output_root)
        print(f"Wrote drop-color debug images for {field_id}")

    print(f"Output folder: {args.output_root}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())