"""Warp a scanned LSCO TDCJ page using detected fiducial squares."""

from __future__ import annotations

import argparse
from pathlib import Path

from lsco_tdcj_intake.imaging.alignment import (
    alignment_summary,
    infer_output_size_from_scan,
    warp_page_from_fiducials,
)
from lsco_tdcj_intake.imaging.fiducials import detect_ordered_fiducials
from lsco_tdcj_intake.imaging.image_io import (
    image_shape_text,
    read_image_bgr,
    read_image_gray,
    write_image,
)


def main() -> None:
    """Detect fiducials and write a normalized warped page image."""
    parser = argparse.ArgumentParser()
    parser.add_argument("image_path", help="Path to scanned page image")
    parser.add_argument(
        "--output",
        default="data/working/debug_warped_page.png",
        help="Path for warped output image",
    )
    args = parser.parse_args()

    image_path = Path(args.image_path)
    output_path = Path(args.output)

    image_bgr = read_image_bgr(image_path)
    gray = read_image_gray(image_path)

    output_width_px, output_height_px = infer_output_size_from_scan(image_bgr)
    ordered = detect_ordered_fiducials(gray)

    warped = warp_page_from_fiducials(
        image=image_bgr,
        ordered_fiducials=ordered,
        output_width_px=output_width_px,
        output_height_px=output_height_px,
    )

    write_image(output_path, warped)

    print(f"Input:  {image_path}")
    print(f"Shape:  {image_shape_text(image_bgr)}")
    print(alignment_summary(ordered, output_width_px, output_height_px))
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()