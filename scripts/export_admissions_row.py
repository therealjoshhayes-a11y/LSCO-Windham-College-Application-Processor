from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PACKET_ID = "image-1"

DEFAULT_REVIEWED_PACKET_JSON = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "review_packets"
    / DEFAULT_PACKET_ID
    / "reviewed_packet.json"
)

DEFAULT_OUTPUT_CSV = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "review_packets"
    / DEFAULT_PACKET_ID
    / "admissions_export_row.csv"
)


ADMISSIONS_HEADERS = [
    "export_status",
    "packet_id",
    "pending_review_count",
    "TXST ID",
    "Last Name",
    "First Name",
    "Middle Name",
    "Date of Birth",
    "Legal Sex",
    "Address - Street",
    "Address - Street 2",
    "Address - City",
    "Address - State",
    "Address - Zip",
    "Address - Country",
    "SSN",
    "Mobile Phone",
    "Phone",
    "Email Address",
    "Emergency - Last",
    "Emergency - First",
    "Emergency - Phone",
    "Emergency - Email",
    "High School - CEEB",
    "High School - Name",
    "College 1 - FICE",
    "College 1 - Name",
    "College 2 - FICE",
    "College 2 - Name",
    "Start Term",
    "Admission Type 1",
    "Admission Type 2",
    "Student Type",
    "Residency Status",
    "Major",
    "First Gen",
]

TERM_LABELS = {
    "fall": "Fall",
    "spring": "Spring",
    "summer": "Summer",
}

STUDENT_TYPE_LABELS = {
    "first_time": "First Time",
    "returning": "Returning",
    "transfer": "Transfer",
}

ADMISSION_TYPE_LABELS = {
    "assoc_deg": "Associate Degree",
    "certificate": "Certificate",
    "enrichment": "Enrichment",
    "transfer": "Transfer",
    "skills_employ": "Skills/Employment",
}

def load_reviewed_packet(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Reviewed packet JSON not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def field_value(packet: dict, field_id: str) -> str:
    fields = packet.get("fields", {})
    field = fields.get(field_id, {})
    return str(field.get("value", "") or "").strip()


def checkbox_selected(packet: dict, field_id: str, output_value: str = "Yes") -> str:
    value = field_value(packet, field_id)
    return output_value if value else ""


def start_term(packet: dict) -> str:
    raw_term = (
        field_value(packet, "p1_term_fall")
        or field_value(packet, "p1_term_spring")
        or field_value(packet, "p1_term_summer")
    )
    year = field_value(packet, "p1_year")

    term = TERM_LABELS.get(raw_term.lower(), raw_term)

    if term and year:
        return f"{term} {year}"

    if term:
        return term

    if year:
        return year

    return ""

def student_type(packet: dict) -> str:
    if field_value(packet, "p1_student_type_first_time"):
        return STUDENT_TYPE_LABELS["first_time"]
    if field_value(packet, "p1_student_type_returning"):
        return STUDENT_TYPE_LABELS["returning"]
    if field_value(packet, "p1_student_type_transfer"):
        return STUDENT_TYPE_LABELS["transfer"]
    return ""


def admission_type(packet: dict) -> str:
    if field_value(packet, "p1_intent_assoc_deg"):
        return ADMISSION_TYPE_LABELS["assoc_deg"]
    if field_value(packet, "p1_intent_certificate"):
        return ADMISSION_TYPE_LABELS["certificate"]
    if field_value(packet, "p1_intent_enrichment"):
        return ADMISSION_TYPE_LABELS["enrichment"]
    if field_value(packet, "p1_intent_transfer"):
        return ADMISSION_TYPE_LABELS["transfer"]
    if field_value(packet, "p1_intent_skills_employ"):
        return ADMISSION_TYPE_LABELS["skills_employ"]
    return ""


def first_gen(packet: dict) -> str:
    bachelors_no = field_value(packet, "p1_bachelors_or_higher_no")
    bachelors_yes = field_value(packet, "p1_bachelors_or_higher_yes")

    if bachelors_no:
        return "Yes"

    if bachelors_yes:
        return "No"

    return ""


def build_export_row(packet: dict) -> dict[str, str]:
    packet_id = str(packet.get("packet_id", "") or "").strip()
    packet_status = str(packet.get("status", "") or "").strip()
    pending_review_count = str(packet.get("pending_review_count", "") or "").strip()

    row = {header: "" for header in ADMISSIONS_HEADERS}

    row["export_status"] = packet_status
    row["packet_id"] = packet_id
    row["pending_review_count"] = pending_review_count

    row["Last Name"] = field_value(packet, "p1_last_name")
    row["First Name"] = field_value(packet, "p1_first_name")
    row["Middle Name"] = field_value(packet, "p1_mi")
    row["Date of Birth"] = field_value(packet, "p1_date_of_birth")
    row["SSN"] = field_value(packet, "p1_ssn")

    row["High School - Name"] = field_value(packet, "p1_hs_name")
    row["College 1 - Name"] = field_value(packet, "p1_prev_college_row1_name")

    row["Start Term"] = start_term(packet)
    row["Admission Type 1"] = admission_type(packet)
    row["Admission Type 2"] = ""
    row["Student Type"] = student_type(packet)

    # Current project defaults / intentionally blank fields.
    row["Address - Country"] = ""
    row["Residency Status"] = ""
    row["Major"] = field_value(packet, "p1_degree_cert_code")
    row["First Gen"] = first_gen(packet)

    return row


def write_one_row(row: dict[str, str], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ADMISSIONS_HEADERS)
        writer.writeheader()
        writer.writerow(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export one draft admissions row from reviewed_packet.json."
    )

    parser.add_argument(
        "--reviewed-packet-json",
        default=str(DEFAULT_REVIEWED_PACKET_JSON),
        help="Input reviewed_packet.json.",
    )

    parser.add_argument(
        "--output-csv",
        default=str(DEFAULT_OUTPUT_CSV),
        help="Output admissions export row CSV.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    reviewed_packet_json = Path(args.reviewed_packet_json).resolve()
    output_csv = Path(args.output_csv).resolve()

    packet = load_reviewed_packet(reviewed_packet_json)
    row = build_export_row(packet)

    write_one_row(row, output_csv)

    print(f"Read reviewed packet JSON: {reviewed_packet_json}")
    print(f"Wrote admissions export row: {output_csv}")
    print(f"Export status: {row['export_status']}")
    print(f"Pending review count: {row['pending_review_count']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())