"""Centroid-based OMR for LSCO TDCJ checkbox fields."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

import cv2
import numpy as np


@dataclass(frozen=True)
class CheckboxOMRConfig:
    dark_threshold: int = 140
    interior_shrink: float = 0.25
    unchecked_max_dark_ratio: float = 0.04
    checked_min_dark_ratio: float = 0.18
    min_interior_size_px: int = 8


@dataclass(frozen=True)
class CheckboxOMRResult:
    field_id: str
    page_number: int
    checked: bool | None
    decision: str
    confidence: float
    dark_pixel_ratio: float
    dark_pixels: int
    measured_pixels: int
    outer_box: tuple[int, int, int, int]
    interior_box: tuple[int, int, int, int]
    config: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _require_checkbox_field(field_id: str, field: Mapping[str, Any]) -> None:
    if field.get("type") != "checkbox":
        raise ValueError(
            f"Field {field_id!r} is not a checkbox field; got {field.get('type')!r}."
        )

    for key in ("cx", "cy", "box_width", "box_height"):
        if key not in field:
            raise ValueError(f"Checkbox field {field_id!r} is missing {key!r}.")


def _page_scale(page_map: Mapping[str, Any], image_shape: tuple[int, ...]) -> tuple[float, float]:
    height_px, width_px = image_shape[:2]
    page_width_pt = float(page_map["width"])
    page_height_pt = float(page_map["height"])
    return width_px / page_width_pt, height_px / page_height_pt


def checkbox_boxes_from_field(
    page_image: np.ndarray,
    page_map: Mapping[str, Any],
    field_id: str,
    field: Mapping[str, Any],
    config: CheckboxOMRConfig | None = None,
) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    cfg = config or CheckboxOMRConfig()
    _require_checkbox_field(field_id, field)

    sx, sy = _page_scale(page_map, page_image.shape)

    cx = float(field["cx"]) * sx
    cy = float(field["cy"]) * sy
    bw = float(field["box_width"]) * sx
    bh = float(field["box_height"]) * sy

    image_h, image_w = page_image.shape[:2]

    x0 = max(0, int(round(cx - bw / 2)))
    y0 = max(0, int(round(cy - bh / 2)))
    x1 = min(image_w, int(round(cx + bw / 2)))
    y1 = min(image_h, int(round(cy + bh / 2)))

    shrink_x = int(round((x1 - x0) * cfg.interior_shrink))
    shrink_y = int(round((y1 - y0) * cfg.interior_shrink))

    ix0 = x0 + shrink_x
    iy0 = y0 + shrink_y
    ix1 = x1 - shrink_x
    iy1 = y1 - shrink_y

    if (ix1 - ix0) < cfg.min_interior_size_px or (iy1 - iy0) < cfg.min_interior_size_px:
        raise ValueError(
            f"Interior checkbox crop for {field_id!r} is too small: "
            f"outer={(x0, y0, x1, y1)}, interior={(ix0, iy0, ix1, iy1)}"
        )

    return (x0, y0, x1, y1), (ix0, iy0, ix1, iy1)


def detect_checkbox_mark(
    page_image: np.ndarray,
    page_map: Mapping[str, Any],
    field_id: str,
    config: CheckboxOMRConfig | None = None,
) -> CheckboxOMRResult:
    cfg = config or CheckboxOMRConfig()

    fields = page_map.get("fields", {})
    if field_id not in fields:
        raise KeyError(f"Field {field_id!r} not found in page map.")

    field = fields[field_id]
    outer_box, interior_box = checkbox_boxes_from_field(
        page_image=page_image,
        page_map=page_map,
        field_id=field_id,
        field=field,
        config=cfg,
    )

    ix0, iy0, ix1, iy1 = interior_box

    if page_image.ndim == 3:
        gray = cv2.cvtColor(page_image, cv2.COLOR_BGR2GRAY)
    else:
        gray = page_image.copy()

    interior = gray[iy0:iy1, ix0:ix1]
    dark_mask = interior <= cfg.dark_threshold

    dark_pixels = int(np.count_nonzero(dark_mask))
    measured_pixels = int(interior.size)
    dark_ratio = dark_pixels / measured_pixels if measured_pixels else 0.0

    if dark_ratio <= cfg.unchecked_max_dark_ratio:
        checked: bool | None = False
        decision = "unchecked"
        confidence = 1.0 - min(
            1.0,
            dark_ratio / max(cfg.unchecked_max_dark_ratio, 1e-9),
        ) * 0.5
    elif dark_ratio >= cfg.checked_min_dark_ratio:
        checked = True
        decision = "checked"
        confidence = 0.5 + min(
            1.0,
            (dark_ratio - cfg.checked_min_dark_ratio) / max(1.0 - cfg.checked_min_dark_ratio, 1e-9),
        ) * 0.5
    else:
        checked = None
        decision = "uncertain"

        band_mid = (cfg.unchecked_max_dark_ratio + cfg.checked_min_dark_ratio) / 2
        band_half = (cfg.checked_min_dark_ratio - cfg.unchecked_max_dark_ratio) / 2
        distance_from_mid = abs(dark_ratio - band_mid)
        confidence = max(
            0.0,
            min(0.49, distance_from_mid / max(band_half, 1e-9) * 0.49),
        )

    return CheckboxOMRResult(
        field_id=field_id,
        page_number=int(page_map.get("page_number", 0)),
        checked=checked,
        decision=decision,
        confidence=round(float(confidence), 4),
        dark_pixel_ratio=round(float(dark_ratio), 6),
        dark_pixels=dark_pixels,
        measured_pixels=measured_pixels,
        outer_box=outer_box,
        interior_box=interior_box,
        config=asdict(cfg),
    )


def draw_checkbox_debug(
    page_image: np.ndarray,
    result: CheckboxOMRResult,
) -> np.ndarray:
    if page_image.ndim == 2:
        debug = cv2.cvtColor(page_image, cv2.COLOR_GRAY2BGR)
    else:
        debug = page_image.copy()

    x0, y0, x1, y1 = result.outer_box
    ix0, iy0, ix1, iy1 = result.interior_box

    cv2.rectangle(debug, (x0, y0), (x1, y1), (0, 0, 255), 3)
    cv2.rectangle(debug, (ix0, iy0), (ix1, iy1), (255, 0, 0), 2)

    label = (
        f"{result.field_id}: {result.decision} "
        f"ratio={result.dark_pixel_ratio:.4f} conf={result.confidence:.2f}"
    )

    label_x = max(0, x0 - 20)
    label_y = max(30, y0 - 20)

    cv2.putText(
        debug,
        label,
        (label_x, label_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 255),
        2,
        cv2.LINE_AA,
    )

    return debug


def save_checkbox_debug_image(
    path: str | Path,
    page_image: np.ndarray,
    result: CheckboxOMRResult,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    debug = draw_checkbox_debug(page_image, result)
    ok = cv2.imwrite(str(path), debug)

    if not ok:
        raise OSError(f"Could not write debug image to {path}")