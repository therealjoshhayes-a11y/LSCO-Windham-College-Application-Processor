"""Page alignment helpers using detected fiducial corner squares."""

from __future__ import annotations

import cv2
import numpy as np

from lsco_tdcj_intake.imaging.fiducials import OrderedFiducials


def target_page_points(width_px: int, height_px: int) -> np.ndarray:
    """Return target corner points for a normalized full-page image."""
    return np.array(
        [
            [0.0, 0.0],
            [float(width_px - 1), 0.0],
            [float(width_px - 1), float(height_px - 1)],
            [0.0, float(height_px - 1)],
        ],
        dtype=np.float32,
    )


def estimate_page_transform(
    ordered_fiducials: OrderedFiducials,
    output_width_px: int,
    output_height_px: int,
) -> np.ndarray:
    """Estimate perspective transform from fiducial centers to page corners."""
    source_points = ordered_fiducials.as_points_float32()
    destination_points = target_page_points(output_width_px, output_height_px)
    return cv2.getPerspectiveTransform(source_points, destination_points)


def warp_page_from_fiducials(
    image: np.ndarray,
    ordered_fiducials: OrderedFiducials,
    output_width_px: int,
    output_height_px: int,
) -> np.ndarray:
    """Warp a scanned page into normalized page geometry."""
    transform = estimate_page_transform(
        ordered_fiducials=ordered_fiducials,
        output_width_px=output_width_px,
        output_height_px=output_height_px,
    )

    return cv2.warpPerspective(
        image,
        transform,
        (output_width_px, output_height_px),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )


def infer_output_size_from_scan(image: np.ndarray) -> tuple[int, int]:
    """Infer normalized output size from input scan dimensions.

    Returns width_px, height_px.
    """
    height, width = image.shape[:2]
    return width, height


def alignment_summary(
    ordered_fiducials: OrderedFiducials,
    output_width_px: int,
    output_height_px: int,
) -> str:
    """Return a compact text summary of the alignment plan."""
    return (
        "fiducial warp "
        f"TL=({ordered_fiducials.top_left.center_x:.1f},{ordered_fiducials.top_left.center_y:.1f}) "
        f"TR=({ordered_fiducials.top_right.center_x:.1f},{ordered_fiducials.top_right.center_y:.1f}) "
        f"BR=({ordered_fiducials.bottom_right.center_x:.1f},{ordered_fiducials.bottom_right.center_y:.1f}) "
        f"BL=({ordered_fiducials.bottom_left.center_x:.1f},{ordered_fiducials.bottom_left.center_y:.1f}) "
        f"-> {output_width_px}x{output_height_px}"
    )