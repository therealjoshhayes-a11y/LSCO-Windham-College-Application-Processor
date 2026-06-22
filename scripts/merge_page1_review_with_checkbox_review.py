from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PACKET_ID = "image-1"

CHECKBOX_REVIEW_CSV = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "checkboxes"
    / PACKET_ID
    / "review_summary.csv"
)

OCR_REVIEW_CSV = (
    PROJECT_ROOT
    / "data"
    / "working"
    / "ocr_debug"
    / "page1_ocr"
    / "page1_review_queue.csv"
)

OUTPUT_CSV = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "review_packets"
    / PACKET_ID
    / "human_review_queue.csv"
)


CHECKBOX_REVIEW_STATUSES = {
    "needs_review",
    "uncertain",
    "invalid",
}

OCR_REVIEW_STATUSES = {
    "ocr_candidate_needs_review",
    "review_needed",
    "needs_review",
    "uncertain",
    "invalid",
}


FIELD_REVIEW_ORDER = {
    # Page 1 OCR identity / enrollment
    "p1_year": 100,
    "p1_ssn": 110,
    "p1_tdcj_number": 120,
    "p1_date_of_birth": 130,
    "p1_former_name": 140,

    # Page 1 OCR education
    "p1_hs_name": 200,
    "p1_hs_state": 210,
    "p1_hs_year": 220,
    "p1_ged_year": 230,
    "p1_prev_college_row1_name": 240,
    "p1_prev_college_row1_city_state": 250,
    "p1_prev_college_row1_years_attended": 260,
    "p1_student_signature_date": 270,

    # Page 1 checkbox groups
    "p1_bachelors_or_higher_no": 300,
    "p1_ethnicity_not_hispanic_latino": 310,

    # Page 2 checkbox groups
    "p2_disclosure_attendance_in_courses": 400,
    "p2_disclosure_grades_in_courses": 410,
    "p2_disclosure_teacher_ratings_observations": 420,
    "p2_disclosure_extracurricular_activities_projects": 430,
    "p2_disclosure_placement_test_scores": 440,
    "p2_disclosure_interest_inventory_results": 450,
    "p2_disclosure_financial_aid_information": 460,
    "p2_disclosure_business_office_transactions": 470,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Required CSV not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def first_present(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = row.get(name, "")
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def review_sort_key(row: dict[str, str]) -> tuple[int, str, str]:
    field_id = row.get("field_id", "")
    order = FIELD_REVIEW_ORDER.get(field_id, 9999)
    return (order, row.get("review_source", ""), field_id)


def normalize_checkbox_row(row: dict[str, str]) -> dict[str, str]:
    field_id = first_present(row, ["field_id", "group_id", "id"])
    status = first_present(row, ["status", "group_status"])

    machine_value = first_present(
        row,
        [
            "machine_value",
            "selected",
            "selected_value",
            "suggested_selected",
            "value",
            "normalized_text",
        ],
    )

    confidence = first_present(
        row,
        [
            "confidence",
            "group_confidence",
            "selected_confidence",
            "suggested_confidence",
        ],
    )

    notes = first_present(
        row,
        [
            "notes",
            "reason",
            "message",
            "validation_message",
            "review_reason",
        ],
    )

    return {
        "packet_id": PACKET_ID,
        "review_source": "checkbox",
        "page": first_present(row, ["page", "page_number"]),
        "field_id": field_id,
        "status": status,
        "machine_value": machine_value,
        "raw_text": "",
        "normalized_text": machine_value,
        "confidence": confidence,
        "numeric_fullfield_candidate": "",
        "numeric_fullfield_variant": "",
        "numeric_fullfield_raw_text": "",
        "notes": notes,
        "crop_path": first_present(
            row,
            [
                "crop_path",
                "debug_crop_path",
                "image_path",
                "debug_image_path",
            ],
        ),
        "processed_numeric_crop_path": "",
        "review_value": "",
        "review_notes": "",
    }


def normalize_ocr_row(row: dict[str, str]) -> dict[str, str]:
    field_id = row.get("field_id", "")
    numeric_candidate = row.get("numeric_fullfield_candidate", "")

    machine_value = first_present(
        row,
        [
            "normalized_text",
            "raw_text",
            "numeric_fullfield_candidate",
        ],
    )

    notes_parts = []

    existing_notes = row.get("notes", "")
    if existing_notes:
        notes_parts.append(existing_notes)

    if numeric_candidate:
        notes_parts.append(
            "numeric full-field evidence is reviewer aid only"
        )

    return {
        "packet_id": PACKET_ID,
        "review_source": "ocr_page1",
        "page": "1",
        "field_id": field_id,
        "status": row.get("status", ""),
        "machine_value": machine_value,
        "raw_text": row.get("raw_text", ""),
        "normalized_text": row.get("normalized_text", ""),
        "confidence": row.get("confidence", ""),
        "numeric_fullfield_candidate": numeric_candidate,
        "numeric_fullfield_variant": row.get("numeric_fullfield_variant", ""),
        "numeric_fullfield_raw_text": row.get("numeric_fullfield_raw_text", ""),
        "notes": " | ".join(notes_parts),
        "crop_path": row.get("crop_path", ""),
        "processed_numeric_crop_path": row.get("processed_numeric_crop_path", ""),
        "review_value": "",
        "review_notes": "",
    }


def with_review_order(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    sorted_rows = sorted(rows, key=review_sort_key)

    output_rows: list[dict[str, str]] = []
    for index, row in enumerate(sorted_rows, start=1):
        output = dict(row)
        output["review_order"] = f"{index:03d}"
        output_rows.append(output)

    return output_rows


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "packet_id",
        "review_order",
        "review_source",
        "page",
        "field_id",
        "status",
        "machine_value",
        "raw_text",
        "normalized_text",
        "confidence",
        "numeric_fullfield_candidate",
        "numeric_fullfield_variant",
        "numeric_fullfield_raw_text",
        "notes",
        "crop_path",
        "processed_numeric_crop_path",
        "review_value",
        "review_notes",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    checkbox_source_rows = read_csv(CHECKBOX_REVIEW_CSV)
    ocr_source_rows = read_csv(OCR_REVIEW_CSV)

    checkbox_review_rows = [
        row
        for row in checkbox_source_rows
        if first_present(row, ["status", "group_status"]) in CHECKBOX_REVIEW_STATUSES
    ]

    ocr_review_rows = [
        row
        for row in ocr_source_rows
        if row.get("status", "") in OCR_REVIEW_STATUSES
    ]

    normalized_rows: list[dict[str, str]] = []

    for row in checkbox_review_rows:
        normalized_rows.append(normalize_checkbox_row(row))

    for row in ocr_review_rows:
        normalized_rows.append(normalize_ocr_row(row))

    final_rows = with_review_order(normalized_rows)
    write_csv(final_rows, OUTPUT_CSV)

    print(f"Read checkbox review CSV: {CHECKBOX_REVIEW_CSV}")
    print(f"Checkbox source rows: {len(checkbox_source_rows)}")
    print(f"Checkbox review rows: {len(checkbox_review_rows)}")
    print(f"Read OCR review CSV: {OCR_REVIEW_CSV}")
    print(f"OCR source rows: {len(ocr_source_rows)}")
    print(f"OCR review rows: {len(ocr_review_rows)}")
    print(f"Wrote merged human review queue: {OUTPUT_CSV}")
    print(f"Total human review rows: {len(final_rows)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())