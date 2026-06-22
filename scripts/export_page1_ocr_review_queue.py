from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PAGE1_OCR_CSV = (
    PROJECT_ROOT
    / "data"
    / "working"
    / "ocr_debug"
    / "page1_ocr"
    / "page1_ocr.csv"
)

NUMERIC_FULLFIELD_CSV = (
    PROJECT_ROOT
    / "data"
    / "working"
    / "ocr_debug"
    / "page1_ocr"
    / "numeric_fullfield"
    / "page1_numeric_fullfield_ocr.csv"
)

OUTPUT_CSV = (
    PROJECT_ROOT
    / "data"
    / "working"
    / "ocr_debug"
    / "page1_ocr"
    / "page1_review_queue.csv"
)


REVIEW_STATUSES = {
    "ocr_candidate_needs_review",
    "review_needed",
    "needs_review",
}


IDENTITY_NUMERIC_FIELDS = {
    "p1_tdcj_number",
    "p1_ssn",
    "p1_date_of_birth",
}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Required CSV not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_optional_numeric_evidence(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    return {row.get("field_id", ""): row for row in rows if row.get("field_id")}


def shape_note(field_id: str, digits: str) -> str:
    if not digits:
        return ""

    digit_count = len(digits)

    if field_id == "p1_ssn":
        return "numeric_shape_valid=True" if digit_count == 9 else "numeric_shape_valid=False; expected exactly 9 digits"

    if field_id == "p1_date_of_birth":
        return "numeric_shape_valid=True" if digit_count == 8 else "numeric_shape_valid=False; expected exactly 8 digits"

    if field_id == "p1_tdcj_number":
        return "numeric_shape_valid=True" if 7 <= digit_count <= 10 else "numeric_shape_valid=False; expected 7 to 10 digits"

    return ""


def first_present(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = row.get(name, "")
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def build_review_row(
    ocr_row: dict[str, str],
    numeric_evidence_by_field: dict[str, dict[str, str]],
) -> dict[str, str]:
    field_id = ocr_row.get("field_id", "")
    numeric = numeric_evidence_by_field.get(field_id, {})

    numeric_digits = numeric.get("best_digits", "")
    numeric_variant = numeric.get("best_variant", "")
    numeric_raw = numeric.get("best_raw_text", "")
    numeric_processed_image = numeric.get("processed_image_path", "")

    notes_parts = []

    existing_notes = ocr_row.get("notes", "")
    if existing_notes:
        notes_parts.append(existing_notes)

    if field_id in IDENTITY_NUMERIC_FIELDS:
        notes_parts.append("identity-critical field; reviewer must verify")
        if numeric_digits:
            notes_parts.append(shape_note(field_id, numeric_digits))

    if numeric_digits:
        notes_parts.append(
            f"numeric_fullfield_candidate={numeric_digits}; "
            f"variant={numeric_variant}; raw={numeric_raw!r}"
        )

    return {
        "field_id": field_id,
        "status": ocr_row.get("status", ""),
        "raw_text": first_present(ocr_row, ["raw_text", "text", "ocr_text"]),
        "normalized_text": first_present(
            ocr_row,
            ["normalized_text", "normalized", "value"],
        ),
        "normalization": ocr_row.get("normalization", ""),
        "confidence": ocr_row.get("confidence", ""),
        "numeric_fullfield_candidate": numeric_digits,
        "numeric_fullfield_variant": numeric_variant,
        "numeric_fullfield_raw_text": numeric_raw,
        "notes": " | ".join(part for part in notes_parts if part),
        "crop_path": first_present(ocr_row, ["crop_path", "image_path", "crop"]),
        "processed_numeric_crop_path": numeric_processed_image,
        "review_value": "",
        "review_notes": "",
    }


def write_review_queue(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "field_id",
        "status",
        "raw_text",
        "normalized_text",
        "normalization",
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
    ocr_rows = read_csv_rows(PAGE1_OCR_CSV)
    numeric_evidence = read_optional_numeric_evidence(NUMERIC_FULLFIELD_CSV)

    review_rows = []

    for row in ocr_rows:
        status = row.get("status", "")
        if status in REVIEW_STATUSES:
            review_rows.append(build_review_row(row, numeric_evidence))

    write_review_queue(review_rows, OUTPUT_CSV)

    print(f"Read OCR CSV: {PAGE1_OCR_CSV}")
    print(f"Read numeric evidence CSV: {NUMERIC_FULLFIELD_CSV if NUMERIC_FULLFIELD_CSV.exists() else 'not found; skipped'}")
    print(f"Wrote review queue: {OUTPUT_CSV}")
    print(f"Review rows: {len(review_rows)}")

    if numeric_evidence:
        enriched = [
            row["field_id"]
            for row in review_rows
            if row.get("numeric_fullfield_candidate")
        ]
        print(f"Rows enriched with numeric full-field evidence: {len(enriched)}")
        for field_id in enriched:
            print(f"  - {field_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())