"""Crop one locked field from a warped LSCO TDCJ page image."""

from __future__ import annotations

import argparse
from pathlib import Path

from lsco_tdcj_intake.form_maps.geometry import field_rect, rect_to_pixel_box
from lsco_tdcj_intake.form_maps.loader import load_all_maps
from lsco_tdcj_intake.imaging.image_io import image_shape_text, read_image_bgr, write_image


# Debug crop profiles are NOT changes to the locked JSON maps.
# They are scan/review crop-window adjustments after fiducial warp.
FIELD_CROP_PROFILES: dict[tuple[int, str], dict[str, int]] = {
    (1, "p1_last_name"): {
        "pad_left": 35,
        "pad_top": 40,
        "pad_right": 20,
        "pad_bottom": -45,
    },
}


def clamp_crop_box(
    left: int,
    top: int,
    right: int,
    bottom: int,
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    """Keep a crop box inside the image bounds."""
    return (
        max(left, 0),
        max(top, 0),
        min(right, image_width),
        min(bottom, image_height),
    )


def resolve_padding(args: argparse.Namespace) -> dict[str, int]:
    """Return field-specific padding, overridden by explicit CLI values."""
    profile = FIELD_CROP_PROFILES.get((args.page, args.field), {})

    return {
        "pad_left": args.pad_left if args.pad_left is not None else profile.get("pad_left", 0),
        "pad_top": args.pad_top if args.pad_top is not None else profile.get("pad_top", 0),
        "pad_right": args.pad_right if args.pad_right is not None else profile.get("pad_right", 0),
        "pad_bottom": args.pad_bottom if args.pad_bottom is not None else profile.get("pad_bottom", 0),
    }


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

    if args.field not in form_map.fields:
        raise KeyError(f"Field not found on page {args.page}: {args.field}")

    padding = resolve_padding(args)

    image = read_image_bgr(Path(args.warped_image_path))
    image_height, image_width = image.shape[:2]

    rect = field_rect(form_map.fields[args.field])
    left, top, right, bottom = rect_to_pixel_box(rect, args.dpi)

    adjusted_left = left - padding["pad_left"]
    adjusted_top = top - padding["pad_top"]
    adjusted_right = right + padding["pad_right"]
    adjusted_bottom = bottom + padding["pad_bottom"]

    adjusted_box = clamp_crop_box(
        adjusted_left,
        adjusted_top,
        adjusted_right,
        adjusted_bottom,
        image_width=image_width,
        image_height=image_height,
    )

    crop_left, crop_top, crop_right, crop_bottom = adjusted_box
    crop = image[crop_top:crop_bottom, crop_left:crop_right]

    if crop.size == 0:
        raise ValueError(
            f"Crop is empty for {args.field}: {adjusted_box} "
            f"from image {image_shape_text(image)}"
        )

    write_image(Path(args.output), crop)

    print(f"Input:     {args.warped_image_path}")
    print(f"Shape:     {image_shape_text(image)}")
    print(f"Page:      {args.page}")
    print(f"Field:     {args.field}")
    print(
        f"Rect:      x={rect.x:.3f}, y={rect.y:.3f}, "
        f"w={rect.width:.3f}, h={rect.height:.3f} pt"
    )
    print(f"Base crop: {(left, top, right, bottom)} px at {args.dpi} dpi")
    print(
        "Padding:   "
        f"L={padding['pad_left']}, T={padding['pad_top']}, "
        f"R={padding['pad_right']}, B={padding['pad_bottom']} px"
    )
    print(f"Final:     {adjusted_box} px")
    print(f"Output:    {args.output}")


if __name__ == "__main__":
    main()