from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OCRProfile:
    profile_id: str
    description: str
    allowlist: str | None
    normalize: str
    min_confidence: float
    review_if_blank: bool = False


OCR_PROFILES: dict[str, OCRProfile] = {
    "boxed_text": OCRProfile(
        profile_id="boxed_text",
        description="General boxed handwriting/text field.",
        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-' ",
        normalize="uppercase_strip",
        min_confidence=0.70,
        review_if_blank=True,
    ),
    "boxed_numeric": OCRProfile(
        profile_id="boxed_numeric",
        description="Boxed numeric field.",
        allowlist="0123456789",
        normalize="digits_only",
        min_confidence=0.75,
        review_if_blank=True,
    ),
    "boxed_date_digits": OCRProfile(
        profile_id="boxed_date_digits",
        description="Boxed date field using digits only.",
        allowlist="0123456789",
        normalize="date_mmddyyyy_digits",
        min_confidence=0.75,
        review_if_blank=True,
    ),
    "state_abbrev": OCRProfile(
        profile_id="state_abbrev",
        description="Two-character US postal state abbreviation.",
        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        normalize="state_abbrev",
        min_confidence=0.55,
        review_if_blank=True,
    ),
    "signature_review_only": OCRProfile(
        profile_id="signature_review_only",
        description="Signature field; crop for reviewer, do not OCR.",
        allowlist=None,
        normalize="review_only",
        min_confidence=1.00,
        review_if_blank=True,
    ),
    "optional_text": OCRProfile(
        profile_id="optional_text",
        description="Optional text field; blank is acceptable.",
        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-' .,/",
        normalize="uppercase_strip",
        min_confidence=0.65,
        review_if_blank=False,
    ),
}


PAGE1_OCR_FIELD_PROFILES: dict[str, str] = {
    "p1_last_name": "boxed_text",
    "p1_first_name": "boxed_text",
    "p1_mi": "boxed_text",
    "p1_former_name": "optional_text",
    "p1_date_of_birth": "boxed_date_digits",
    "p1_tdcj_number": "boxed_numeric",
    "p1_ssn": "boxed_numeric",
    "p1_alien_reg_no": "optional_text",
    "p1_degree_cert_code": "optional_text",
    "p1_ged_year": "boxed_numeric",
    "p1_hs_name": "boxed_text",
    "p1_hs_state": "state_abbrev",
    "p1_hs_year": "boxed_numeric",
    "p1_prev_college_row1_name": "optional_text",
    "p1_prev_college_row1_city_state": "optional_text",
    "p1_prev_college_row1_years_attended": "optional_text",
    "p1_prev_college_row2_name": "optional_text",
    "p1_prev_college_row2_city_state": "optional_text",
    "p1_prev_college_row2_years_attended": "optional_text",
    "p1_prev_college_row3_name": "optional_text",
    "p1_prev_college_row3_city_state": "optional_text",
    "p1_prev_college_row3_years_attended": "optional_text",
    "p1_student_signature": "signature_review_only",
    "p1_student_signature_date": "boxed_date_digits",
    "p1_year": "boxed_numeric",
}


US_STATE_ABBREVIATIONS: set[str] = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}


def get_profile_for_page1_field(field_id: str) -> OCRProfile:
    profile_id = PAGE1_OCR_FIELD_PROFILES.get(field_id)

    if profile_id is None:
        raise KeyError(f"No Page 1 OCR profile configured for field: {field_id}")

    return OCR_PROFILES[profile_id]


def page1_ocr_field_ids() -> list[str]:
    return list(PAGE1_OCR_FIELD_PROFILES.keys())