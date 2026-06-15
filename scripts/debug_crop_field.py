"""Crop one locked field from a warped LSCO TDCJ page image."""

from __future__ import annotations

import argparse
from pathlib import Path

from lsco_tdcj_intake.form_maps.loader import load_all_maps
from lsco_tdcj_intake.imaging.field_cropper import (
    CropPadding,
    crop_field_from_file,
    save_crop_result,
)
from lsco_tdcj_intake.imaging.image_io import image_shape_text, read_image_bgr


def resolve_padding_override(args: argparse.Namespace) -> CropPadding | None:
    """Return CLI crop padding override if any pad value was provided."""
    values = [args.pad_left, args.pad_top, args.pad_right, args.pad_bottom]
    if all(value is None for value in values):
        return None

    return CropPadding(
        left=args.pad_left or 0,
        top=args.pad_top or 0,
        right=args.pad_right or 0,
        bottom=args.pad_bottom or 0,
    )


def main() -> None:
    """Crop one mapped field from an already-warped page image."""
    parser = argparse.ArgumentParser()
    parser.add_argument("warped_image_path", help="Path to warped page image")
    parser.add_argument("--page", type=int, required=True, choices=[1, 2])
    parser.add_argument("--field", required=True, help="Locked field ID to crop")
    parser.add_argument("--dpi", type=int, default=600)

    parser.add_argument("--pad-left", type=int, default=None)
    parser.add_argument("--pad-top", type=int, default=None)
    parser.add_argument("--pad-right", type=int, default=None)
    parser.add_argument("--pad-bottom", type=int, default=None)

    parser.add_argument(
        "--output",
        default="data/working/debug_field_crop.png",
        help="Path for cropped field output image",
    )
    args = parser.parse_args()

    maps = load_all_maps()
    form_map = maps[args.page]
    padding_override = resolve_padding_override(args)

    result = crop_field_from_file(
        warped_image_path=Path(args.warped_image_path),
        form_map=form_map,
        field_id=args.field,
        dpi=args.dpi,
        padding=padding_override,
    )
    save_crop_result(result, Path(args.output))

    image = read_image_bgr(Path(args.warped_image_path))

    print(f"Input:     {args.warped_image_path}")
    print(f"Shape:     {image_shape_text(image)}")
    print(f"Page:      {result.page_number}")
    print(f"Field:     {result.field_id}")
    print(
        f"Rect:      x={result.rect.x:.3f}, y={result.rect.y:.3f}, "
        f"w={result.rect.width:.3f}, h={result.rect.height:.3f} pt"
    )
    print(f"Base crop: {result.base_box} px at {args.dpi} dpi")
    print(
        "Padding:   "
        f"L={result.padding.left}, T={result.padding.top}, "
        f"R={result.padding.right}, B={result.padding.bottom} px"
    )
    print(f"Final:     {result.final_box} px")
    print(f"Output:    {args.output}")


if __name__ == "__main__":
    main()