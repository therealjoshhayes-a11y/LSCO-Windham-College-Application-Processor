"""Print crop rectangles for selected locked form fields."""

from __future__ import annotations

from lsco_tdcj_intake.form_maps.geometry import field_rect, rect_to_pixel_box
from lsco_tdcj_intake.form_maps.loader import load_all_maps


DEFAULT_DPI = 300


def main() -> None:
    """Print point-space and pixel-space rectangles for important fields."""
    maps = load_all_maps()

    targets = {
        1: [
            "p1_last_name",
            "p1_first_name",
            "p1_ssn",
            "p1_date_of_birth",
            "p1_student_type_first_time",
            "p1_prev_college_row1_name",
            "p1_student_signature",
        ],
        2: [
            "p2_sectionA_student_name",
            "p2_sectionA_row1_name_or_org",
            "p2_disclosure_attendance_in_courses",
            "p2_sectionB_name",
            "p2_sectionB_tdcj_number",
            "p2_sectionB_student_offender_signature",
        ],
    }

    print(f"Debug field rectangles at {DEFAULT_DPI} dpi")
    print("=" * 40)

    for page_number, field_ids in targets.items():
        form_map = maps[page_number]
        print()
        print(f"Page {page_number}")

        for field_id in field_ids:
            field = form_map.fields[field_id]
            rect = field_rect(field)
            pixel_box = rect_to_pixel_box(rect, DEFAULT_DPI)
            print(f"  {field_id}")
            print(
                f"    pt: x={rect.x:.3f}, y={rect.y:.3f}, "
                f"w={rect.width:.3f}, h={rect.height:.3f}"
            )
            print(f"    px: {pixel_box}")


if __name__ == "__main__":
    main()