"""Geometry helpers for locked LSCO TDCJ form maps.

Map coordinates are stored in PDF points at 72 dpi.
Scanned images are processed in pixels, usually 300 or 600 dpi.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


POINTS_PER_INCH = 72.0


@dataclass(frozen=True)
class Rect:
    """Rectangle in page coordinate space."""

    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        """Return right edge."""
        return self.x + self.width

    @property
    def bottom(self) -> float:
        """Return bottom edge."""
        return self.y + self.height

    @property
    def center_x(self) -> float:
        """Return horizontal center."""
        return self.x + (self.width / 2.0)

    @property
    def center_y(self) -> float:
        """Return vertical center."""
        return self.y + (self.height / 2.0)


@dataclass(frozen=True)
class Scale:
    """Scale factor from PDF points to image pixels."""

    dpi: int

    @property
    def factor(self) -> float:
        """Return pixels per PDF point."""
        return self.dpi / POINTS_PER_INCH

    def pt_to_px(self, value: float) -> int:
        """Convert one point value to nearest integer pixel."""
        return int(round(value * self.factor))

    def px_to_pt(self, value: float) -> float:
        """Convert one pixel value to points."""
        return value / self.factor


def rect_from_region(field: dict[str, Any]) -> Rect:
    """Build a rectangle from a free-text or locked-zone style field."""
    return Rect(
        x=float(field["x"]),
        y=float(field["y"]),
        width=float(field["width"]),
        height=float(field["height"]),
    )


def rect_from_checkbox(field: dict[str, Any], padding_pt: float = 2.0) -> Rect:
    """Build a padded rectangle around a checkbox centroid."""
    box_width = float(field["box_width"]) + (padding_pt * 2)
    box_height = float(field["box_height"]) + (padding_pt * 2)
    return Rect(
        x=float(field["cx"]) - (box_width / 2.0),
        y=float(field["cy"]) - (box_height / 2.0),
        width=box_width,
        height=box_height,
    )


def rect_from_boxed_series(field: dict[str, Any], padding_pt: float = 2.0) -> Rect:
    """Build a padded rectangle around a boxed text series."""
    char_count = int(field["char_count"])
    cell_width = float(field["cell_width"])
    start_x = float(field["start_x"])
    center_y = float(field["center_y"])

    width = (char_count * cell_width) + (padding_pt * 2)
    height = cell_width + (padding_pt * 2)

    return Rect(
        x=start_x - (cell_width / 2.0) - padding_pt,
        y=center_y - (cell_width / 2.0) - padding_pt,
        width=width,
        height=height,
    )


def rect_from_boxed_cells(field: dict[str, Any], padding_pt: float = 2.0) -> Rect:
    """Build a padded rectangle around explicit boxed-text cell centers."""
    cells = field["cells"]
    if not cells:
        raise ValueError("boxed_text_cells field has no cells")

    xs = [float(cell["cx"]) for cell in cells]
    ys = [float(cell["cy"]) for cell in cells]

    if len(xs) > 1:
        inferred_cell_width = min(
            abs(xs[index + 1] - xs[index])
            for index in range(len(xs) - 1)
            if abs(xs[index + 1] - xs[index]) > 0
        )
    else:
        inferred_cell_width = 21.26

    min_x = min(xs) - (inferred_cell_width / 2.0) - padding_pt
    max_x = max(xs) + (inferred_cell_width / 2.0) + padding_pt
    min_y = min(ys) - (inferred_cell_width / 2.0) - padding_pt
    max_y = max(ys) + (inferred_cell_width / 2.0) + padding_pt

    return Rect(x=min_x, y=min_y, width=max_x - min_x, height=max_y - min_y)


def rect_from_line_text(field: dict[str, Any], padding_pt: float = 4.0) -> Rect:
    """Build a rectangle around a line-text baseline."""
    return Rect(
        x=float(field["start_x"]) - padding_pt,
        y=float(field["baseline_y"]) - 18.0,
        width=float(field["max_width"]) + (padding_pt * 2),
        height=24.0,
    )


def field_rect(field: dict[str, Any]) -> Rect:
    """Return the best crop rectangle for a mapped field."""
    field_type = field.get("type")

    if field_type == "checkbox":
        return rect_from_checkbox(field)
    if field_type == "boxed_text_series":
        return rect_from_boxed_series(field)
    if field_type == "boxed_text_cells":
        return rect_from_boxed_cells(field)
    if field_type == "free_text_region":
        return rect_from_region(field)
    if field_type == "line_text":
        return rect_from_line_text(field)

    raise ValueError(f"Cannot create field rectangle for field type: {field_type}")


def rect_to_pixel_box(rect: Rect, dpi: int) -> tuple[int, int, int, int]:
    """Convert a point-space rectangle to a PIL/OpenCV crop box in pixels.

    Returns left, top, right, bottom.
    """
    scale = Scale(dpi=dpi)
    left = scale.pt_to_px(rect.x)
    top = scale.pt_to_px(rect.y)
    right = scale.pt_to_px(rect.right)
    bottom = scale.pt_to_px(rect.bottom)
    return left, top, right, bottom