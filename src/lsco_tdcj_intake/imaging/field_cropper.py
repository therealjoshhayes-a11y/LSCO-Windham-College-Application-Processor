"""Reusable field cropping from warped LSCO TDCJ page images."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from lsco_tdcj_intake.form_maps.geometry import Rect, field_rect, rect_to_pixel_box
from lsco_tdcj_intake.form_maps.loader import FormMap
from lsco_tdcj_intake.imaging.image_io import read_image_bgr, write_image


@dataclass(frozen=True)
class CropPadding:
    """Pixel padding around a field crop."""

    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0


@dataclass(frozen=True)
class FieldCropResult:
    """Result of cropping one mapped field."""

    page_number: int
    field_id: str
    rect: Rect
    base_box: tuple[int, int, int, int]
    final_box: tuple[int, int, int, int]
    padding: CropPadding
    image: np.ndarray


# These are scan/review crop-window adjustments after fiducial warp.
# They are NOT changes to the locked JSON maps.
FIELD_CROP_PROFILES: dict[tuple[int, str], CropPadding] = {
    (1, "p1_last_name"): CropPadding(left=35, top=40, right=20, bottom=-45),
    (1, "p1_student_type_first_time"): CropPadding(left=140, top=-45, right=-115, bottom=20),
    (2, "p2_sectionB_name"): CropPadding(left=110, top=-15, right=10, bottom=35),
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


def get_crop_padding(
    page_number: int,
    field_id: str,
    override: CropPadding | None = None,
) -> CropPadding:
    """Return field-specific padding unless an override is supplied."""
    if override is not None:
        return override

    return FIELD_CROP_PROFILES.get((page_number, field_id), CropPadding())


def crop_field_from_image(
    image: np.ndarray,
    form_map: FormMap,
    field_id: str,
    dpi: int,
    padding: CropPadding | None = None,
) -> FieldCropResult:
    """Crop one field from a warped page image."""
    if field_id not in form_map.fields:
        raise KeyError(f"Field not found on page {form_map.page_number}: {field_id}")

    image_height, image_width = image.shape[:2]

    resolved_padding = get_crop_padding(
        page_number=form_map.page_number,
        field_id=field_id,
        override=padding,
    )

    rect = field_rect(form_map.fields[field_id])
    left, top, right, bottom = rect_to_pixel_box(rect, dpi)

    adjusted_box = clamp_crop_box(
        left - resolved_padding.left,
        top - resolved_padding.top,
        right + resolved_padding.right,
        bottom + resolved_padding.bottom,
        image_width=image_width,
        image_height=image_height,
    )

    crop_left, crop_top, crop_right, crop_bottom = adjusted_box
    crop_image = image[crop_top:crop_bottom, crop_left:crop_right]

    if crop_image.size == 0:
        raise ValueError(
            f"Crop is empty for page {form_map.page_number} field {field_id}: "
            f"{adjusted_box}"
        )

    return FieldCropResult(
        page_number=form_map.page_number,
        field_id=field_id,
        rect=rect,
        base_box=(left, top, right, bottom),
        final_box=adjusted_box,
        padding=resolved_padding,
        image=crop_image,
    )


def crop_field_from_file(
    warped_image_path: Path | str,
    form_map: FormMap,
    field_id: str,
    dpi: int,
    padding: CropPadding | None = None,
) -> FieldCropResult:
    """Read a warped page image and crop one field."""
    image = read_image_bgr(warped_image_path)
    return crop_field_from_image(
        image=image,
        form_map=form_map,
        field_id=field_id,
        dpi=dpi,
        padding=padding,
    )


def save_crop_result(result: FieldCropResult, output_path: Path | str) -> Path:
    """Save a field crop image."""
    return write_image(output_path, result.image)