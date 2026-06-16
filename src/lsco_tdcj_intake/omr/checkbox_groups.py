"""Checkbox group definitions and interpretation for LSCO TDCJ forms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from lsco_tdcj_intake.omr.checkbox import CheckboxOMRResult


GroupRule = Literal["exactly_one", "zero_or_more", "one_or_more"]


@dataclass(frozen=True)
class CheckboxOption:
    value: str
    field_id: str
    label: str


@dataclass(frozen=True)
class CheckboxGroup:
    page_number: int
    group_id: str
    label: str
    rule: GroupRule
    options: tuple[CheckboxOption, ...]


CHECKBOX_GROUPS: dict[tuple[int, str], CheckboxGroup] = {
    (1, "student_type"): CheckboxGroup(
        page_number=1,
        group_id="student_type",
        label="Student Type",
        rule="exactly_one",
        options=(
            CheckboxOption("first_time", "p1_student_type_first_time", "First Time"),
            CheckboxOption("returning", "p1_student_type_returning", "Returning"),
            CheckboxOption("transfer", "p1_student_type_transfer", "Transfer"),
        ),
    ),
    (1, "term"): CheckboxGroup(
        page_number=1,
        group_id="term",
        label="Term",
        rule="exactly_one",
        options=(
            CheckboxOption("fall", "p1_term_fall", "Fall"),
            CheckboxOption("spring", "p1_term_spring", "Spring"),
            CheckboxOption("summer", "p1_term_summer", "Summer"),
        ),
    ),
    (1, "intent"): CheckboxGroup(
        page_number=1,
        group_id="intent",
        label="Intent",
        rule="exactly_one",
        options=(
            CheckboxOption("assoc_deg", "p1_intent_assoc_deg", "Assoc. Deg."),
            CheckboxOption("certificate", "p1_intent_certificate", "Certificate"),
            CheckboxOption("enrichment", "p1_intent_enrichment", "Enrichment"),
            CheckboxOption("transfer", "p1_intent_transfer", "Transfer"),
            CheckboxOption("skills_employ", "p1_intent_skills_employ", "Skills/Employ."),
        ),
    ),
    (1, "ethnicity"): CheckboxGroup(
        page_number=1,
        group_id="ethnicity",
        label="Ethnicity",
        rule="exactly_one",
        options=(
            CheckboxOption("hispanic_latino", "p1_ethnicity_hispanic_latino", "Hispanic/Latino"),
            CheckboxOption("not_hispanic_latino", "p1_ethnicity_not_hispanic_latino", "Not Hispanic/Latino"),
        ),
    ),
    (1, "race"): CheckboxGroup(
        page_number=1,
        group_id="race",
        label="Race",
        rule="one_or_more",
        options=(
            CheckboxOption("white", "p1_race_white", "White"),
            CheckboxOption("black_african_american", "p1_race_black_african_american", "Black/African American"),
            CheckboxOption("asian", "p1_race_asian", "Asian"),
            CheckboxOption("american_indian", "p1_race_american_indian", "American Indian"),
            CheckboxOption("native_hawaiian_pacific_islander", "p1_race_native_hawaiian_pacific_islander", "Native Hawaiian/Pacific Islander"),
            CheckboxOption("two_or_more", "p1_race_two_or_more", "Two or More"),
            CheckboxOption("unknown", "p1_race_unknown", "Unknown"),
        ),
    ),
    (1, "citizenship"): CheckboxGroup(
        page_number=1,
        group_id="citizenship",
        label="Citizenship",
        rule="exactly_one",
        options=(
            CheckboxOption("us_citizen", "p1_citizenship_us_citizen", "U.S. Citizen"),
            CheckboxOption("permanent_resident_alien", "p1_citizenship_permanent_resident_alien", "Permanent Resident Alien"),
        ),
    ),
    (1, "hs_graduate"): CheckboxGroup(
        page_number=1,
        group_id="hs_graduate",
        label="HS Graduate",
        rule="exactly_one",
        options=(
            CheckboxOption("yes", "p1_hs_graduate_yes", "Yes"),
            CheckboxOption("no", "p1_hs_graduate_no", "No"),
        ),
    ),
    (1, "ged"): CheckboxGroup(
        page_number=1,
        group_id="ged",
        label="GED",
        rule="exactly_one",
        options=(
            CheckboxOption("yes", "p1_ged_yes", "Yes"),
            CheckboxOption("no", "p1_ged_no", "No"),
        ),
    ),
    (1, "bachelors_or_higher"): CheckboxGroup(
        page_number=1,
        group_id="bachelors_or_higher",
        label="Bachelor's or Higher",
        rule="exactly_one",
        options=(
            CheckboxOption("yes", "p1_bachelors_or_higher_yes", "Yes"),
            CheckboxOption("no", "p1_bachelors_or_higher_no", "No"),
        ),
    ),
        (2, "disclosure_allowed"): CheckboxGroup(
        page_number=2,
        group_id="disclosure_allowed",
        label="Disclosure Allowed",
        rule="zero_or_more",
        options=(
            CheckboxOption("attendance_in_courses", "p2_disclosure_attendance_in_courses", "Attendance in course(s)"),
            CheckboxOption("grades_in_courses", "p2_disclosure_grades_in_courses", "Grades in course(s)"),
            CheckboxOption("teacher_ratings_observations", "p2_disclosure_teacher_ratings_observations", "Teacher ratings/observations"),
            CheckboxOption("extracurricular_activities_projects", "p2_disclosure_extracurricular_activities_projects", "Extracurricular Activities/Projects"),
            CheckboxOption("placement_test_scores", "p2_disclosure_placement_test_scores", "Placement test scores"),
            CheckboxOption("interest_inventory_results", "p2_disclosure_interest_inventory_results", "Interest Inventory results"),
            CheckboxOption("financial_aid_information", "p2_disclosure_financial_aid_information", "Financial Aid information"),
            CheckboxOption("business_office_transactions", "p2_disclosure_business_office_transactions", "Business Office transactions"),
        ),
    ),
}


def get_checkbox_group(page_number: int, group_id: str) -> CheckboxGroup:
    key = (page_number, group_id)

    if key not in CHECKBOX_GROUPS:
        known = ", ".join(f"page {p} / {g}" for p, g in sorted(CHECKBOX_GROUPS))
        raise KeyError(f"Unknown checkbox group page={page_number} group={group_id!r}. Known: {known}")

    return CHECKBOX_GROUPS[key]


def interpret_checkbox_group(
    group: CheckboxGroup,
    results: dict[str, CheckboxOMRResult],
) -> dict:
    selected: list[str] = []
    uncertain: list[str] = []
    suggested_selected: list[str] = []
    fields: dict[str, dict] = {}

    for option in group.options:
        result = results[option.field_id]

        fields[option.field_id] = {
            "value": option.value,
            "label": option.label,
            "decision": result.decision,
            "checked": result.checked,
            "confidence": result.confidence,
            "dark_pixel_ratio": result.dark_pixel_ratio,
            "outer_box": result.outer_box,
            "interior_box": result.interior_box,
        }

        if result.checked is True:
            selected.append(option.value)
        elif result.checked is None:
            uncertain.append(option.value)

    # Conservative rescue suggestion:
    # If exactly one option is uncertain, all others are clearly unchecked,
    # and the group requires exactly one, suggest it for human review.
    # Do not mark it selected automatically.
    if group.rule == "exactly_one" and not selected and len(uncertain) == 1:
        suggested_selected = uncertain.copy()

    if uncertain:
        status = "needs_review"

        if suggested_selected:
            message = (
                f"Likely selected {suggested_selected[0]}; "
                "mark is below checked threshold and requires review."
            )
        else:
            message = f"Uncertain checkbox result(s): {', '.join(uncertain)}"

    elif group.rule == "exactly_one" and len(selected) == 1:
        status = "valid"
        message = f"Selected {selected[0]}"

    elif group.rule == "exactly_one" and len(selected) == 0:
        status = "invalid"
        message = "No option selected; exactly one required."

    elif group.rule == "exactly_one" and len(selected) > 1:
        status = "invalid"
        message = f"Multiple options selected: {', '.join(selected)}"

    elif group.rule == "one_or_more" and len(selected) >= 1:
        status = "valid"
        message = f"Selected {', '.join(selected)}"

    elif group.rule == "one_or_more":
        status = "invalid"
        message = "No option selected; one or more required."

    else:
        status = "valid"
        message = f"Selected {', '.join(selected)}" if selected else "No options selected."

    return {
        "page_number": group.page_number,
        "group_id": group.group_id,
        "label": group.label,
        "rule": group.rule,
        "status": status,
        "message": message,
        "selected": selected,
        "suggested_selected": suggested_selected,
        "uncertain": uncertain,
        "fields": fields,
    }