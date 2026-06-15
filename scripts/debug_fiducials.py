"""Detect and draw LSCO TDCJ page fiducial squares on a scanned image."""

from __future__ import annotations

import argparse
from pathlib import Path

from lsco_tdcj_intake.imaging.fiducials import (
    detect_ordered_fiducials,
    draw_fiducial_debug,
    find_square_candidates,
)
from lsco_tdcj_intake.imaging.image_io import (
    image_shape_text,
    read_image_bgr,
    read_image_gray,
    write_image,
)


def main() -> None:
    """Run fiducial detection on one image file."""
    parser = argparse.ArgumentParser()
    parser.add_argument("image_path", help="Path to scanned page image")
    parser.add_argument(
        "--output",
        default="data/working/debug_fiducials.png",
        help="Path for labeled debug image",
    )
    args = parser.parse_args()

    image_path = Path(args.image_path)
    output_path = Path(args.output)

    image_bgr = read_image_bgr(image_path)
    gray = read_image_gray(image_path)

    candidates = find_square_candidates(gray)
    ordered = detect_ordered_fiducials(gray)
    debug_image = draw_fiducial_debug(image_bgr, ordered)
    write_image(output_path, debug_image)

    print(f"Input:      {image_path}")
    print(f"Shape:      {image_shape_text(image_bgr)}")
    print(f"Candidates: {len(candidates)}")
    print("Ordered fiducials:")
    print(f"  TL: ({ordered.top_left.center_x:.1f}, {ordered.top_left.center_y:.1f})")
    print(f"  TR: ({ordered.top_right.center_x:.1f}, {ordered.top_right.center_y:.1f})")
    print(f"  BR: ({ordered.bottom_right.center_x:.1f}, {ordered.bottom_right.center_y:.1f})")
    print(f"  BL: ({ordered.bottom_left.center_x:.1f}, {ordered.bottom_left.center_y:.1f})")
    print(f"Output:     {output_path}")


if __name__ == "__main__":
    main()